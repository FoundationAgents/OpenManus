import { AgentBay } from "../../src";
import fetch from "node-fetch";
import { log } from "../../src/utils/logger";

// Skip in CI if no API key, Jest will still collect but we handle at runtime
const apiKey = process.env.AGENTBAY_API_KEY || "";

describe("Context File URLs Integration", () => {
	let agentBay: AgentBay;
	let contextId = "";
	let context!: { id: string; name: string };

	beforeAll(async () => {
		if (!apiKey || process.env.CI) {
			return;
		}
		agentBay = new AgentBay({ apiKey });

		const contextName = `test-file-url-ts-${Date.now()}`;
		const ctxRes = await agentBay.context.get(contextName, true);
		if (!ctxRes.success || !ctxRes.context) {
			return;
		}
		context = ctxRes.context as any;
		contextId = context.id;
		log(`Created context: ${context.name} (ID: ${contextId})`);
	});

	afterAll(async () => {
		if (!apiKey || process.env.CI) {
			return;
		}
		if (contextId) {
			try {
				await agentBay.context.delete(context as any);
				log(`Deleted context: ${context.name} (ID: ${contextId})`);
			} catch (e) {
				log(`Warning: Failed to delete context ${context.name}: ${e}`);
			}
		}
	});

	it("should get upload and download URLs, verify content and list/delete with retries", async () => {
		if (!apiKey || process.env.CI) {
			return;
		}

		const testPath = "/tmp/integration_upload_test.txt";

		// 1) Get upload URL
		const uploadURLRes = await agentBay.context.getFileUploadUrl(contextId, testPath);
		expect(uploadURLRes.requestId).toBeDefined();
		expect(uploadURLRes.success).toBe(true);
		expect(typeof uploadURLRes.url).toBe("string");
		expect(uploadURLRes.url.length).toBeGreaterThan(0);
		log(`Upload URL: ${uploadURLRes.url.slice(0, 80)}... (RequestID: ${uploadURLRes.requestId})`);

		// 2) Upload content using the presigned URL
		const uploadContent = Buffer.from(`agentbay integration upload test at ${Date.now()}\n`, "utf-8");
		const putResp = await fetch(uploadURLRes.url, { method: "PUT", body: uploadContent });
		expect([200, 204]).toContain(putResp.status);
		const etag = putResp.headers.get("etag");
		log(`Uploaded ${uploadContent.length} bytes, status=${putResp.status}, ETag=${etag}`);

		// 3) Get download URL and verify content
		const dlURLRes = await agentBay.context.getFileDownloadUrl(contextId, testPath);
		expect(dlURLRes.success).toBe(true);
		expect(typeof dlURLRes.url).toBe("string");
		expect(dlURLRes.url.length).toBeGreaterThan(0);
		log(`Download URL: ${dlURLRes.url.slice(0, 80)}... (RequestID: ${dlURLRes.requestId})`);

		const dlResp = await fetch(dlURLRes.url);
		expect(dlResp.status).toBe(200);
		const dlBuf = Buffer.from(await dlResp.arrayBuffer());
		expect(Buffer.compare(dlBuf, uploadContent)).toBe(0);
		log(`Downloaded ${dlBuf.length} bytes, content matches uploaded data`);

		// 4) List files to verify presence of the uploaded file under /tmp (with small retry)
		const fileName = "integration_upload_test.txt";

		const listContains = async () => {
			const res = await agentBay.context.listFiles(contextId, "/tmp", 1, 50);
			if (!res || !res.success) {
				return [false, res, "/tmp"] as [boolean, any, string];
			}
			let found = false;
			for (const e of res.entries || []) {
				if (!e) continue;
				if (e.filePath === testPath || e.fileName === fileName) {
					found = true;
					break;
				}
			}
			if (found || (res.entries && res.entries.length > 0)) {
				return [found, res, "/tmp"] as [boolean, any, string];
			}
			return [false, res, "/tmp"] as [boolean, any, string];
		};

		let present = false;
		let lastListRes: any = null;
		let chosenParent = "";
		let retriesPresence = 0;
		for (let i = 0; i < 30; i++) {
			const [p, r, parent] = await listContains();
			present = p;
			lastListRes = r;
			chosenParent = parent;
			if (present) {
				break;
			}
			retriesPresence++;
			await new Promise((res) => setTimeout(res, 2000));
		}
		log(`List files retry attempts (presence check): ${retriesPresence}`);

		if (lastListRes && chosenParent) {
			const total = typeof lastListRes.count === "number" ? lastListRes.count : (lastListRes.entries?.length || 0);
			log(`List files: checked parent=${chosenParent}, total=${total}, contains=${present}`);
		} else {
			log("List files: no listing result available");
		}

		if (lastListRes && lastListRes.entries && lastListRes.entries.length > 0) {
			expect(present).toBe(true);
		}

		// 5) Delete the file and verify it disappears from listing (with small retry)
		const delRes = await agentBay.context.deleteFile(contextId, testPath);
		expect(delRes.success).toBe(true);
		log(`Deleted file: ${testPath}`);

		let removed = false;
		let retriesDeletion = 0;
		for (let i = 0; i < 20; i++) {
			const [p] = await listContains();
			if (lastListRes && lastListRes.entries && lastListRes.entries.length > 0) {
				if (!p) {
					removed = true;
					break;
				}
				removed = false;
			} else {
				removed = true;
				break;
			}
			retriesDeletion++;
			await new Promise((res) => setTimeout(res, 1000));
		}
		log(`List files retry attempts (deletion check): ${retriesDeletion}`);
		expect(removed).toBe(true);
		if (lastListRes) {
			const prev = typeof lastListRes.count === "number" ? lastListRes.count : (lastListRes.entries?.length || 0);
			log(`List files: ${fileName} absent after delete (listing availability: ${prev})`);
		}

		// 6) Attempt to download after delete and log the status (informational)
		const postDL = await agentBay.context.getFileDownloadUrl(contextId, testPath);
		if (postDL && postDL.success && postDL.url && postDL.url.length > 0) {
			const postResp = await fetch(postDL.url);
			log(`Post-delete download status (informational): ${postResp.status}`);
		} else {
			log("Post-delete: download URL not available, treated as deleted");
		}
	});
}); 