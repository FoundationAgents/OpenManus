import { AgentBay, logError, log } from 'wuying-agentbay-sdk';

// Define test path prefix
const TestPathPrefix = '/tmp';

// Define interfaces for file system operations
interface FileEntry {
  name: string;
  isDirectory: boolean;
  size?: number;
  path?: string;
}

async function main() {
  // Get API key from environment variable or use default value for testing
  const apiKey = process.env.AGENTBAY_API_KEY || 'akm-xxx'; // Replace with your actual API key
  if (!process.env.AGENTBAY_API_KEY) {
    log('Warning: Using placeholder API key. Set AGENTBAY_API_KEY environment variable for production use.');
  }

  // Initialize the AgentBay client
  const agentBay = new AgentBay({ apiKey });

  // Create a new session
  log('\nCreating a new session...');
  const createResponse = await agentBay.create({imageId:'linux_latest'});
  const session = createResponse.session;
  log(`\nSession created with ID: ${session.sessionId}`);
  log(`Create Session RequestId: ${createResponse.requestId}`);

  try {
    // 1. Create a directory
    const testDirPath = `${TestPathPrefix}/test_directory`;
    log(`\nCreating directory: ${testDirPath}`);
    try {
      const createDirResponse = await session.fileSystem.createDirectory(testDirPath);
      log(`Directory created: ${createDirResponse.success}`);
      log(`Create Directory RequestId: ${createDirResponse.requestId}`);
    } catch (error) {
      log(`Error creating directory: ${error}`);
    }

    // 2. Write a file
    const testFilePath = `${TestPathPrefix}/test_directory/sample.txt`;
    const testContent = "This is a sample file content.\nThis is the second line.\nThis is the third line.";
    log(`\nWriting file: ${testFilePath}`);
    try {
      const writeResponse = await session.fileSystem.writeFile(testFilePath, testContent, "overwrite");
      log(`File written successfully: ${writeResponse.success}`);
      log(`Write File RequestId: ${writeResponse.requestId}`);
    } catch (error) {
      log(`Error writing file: ${error}`);
    }

    // 3. Read the file we just created
    log(`\nReading file: ${testFilePath}`);
    try {
      const readResponse = await session.fileSystem.readFile(testFilePath);
      log(`File content:\n${readResponse.content}`);
      log(`Read File RequestId: ${readResponse.requestId}`);

      // Verify content matches what we wrote
      if (readResponse.content === testContent) {
        log('Content verification successful!');
      } else {
        log('Content verification failed!');
      }
    } catch (error) {
      log(`Error reading file: ${error}`);
    }

    // 4. Get file info
    log(`\nGetting file info for: ${testFilePath}`);
    try {
      const fileInfoResponse = await session.fileSystem.getFileInfo(testFilePath);
      const fileInfo = fileInfoResponse.fileInfo;
      log(`File info: Name=${fileInfo.name}, Path=${fileInfo.path}, Size=${fileInfo.size}, IsDirectory=${fileInfo.isDirectory}`);
      log(`Get File Info RequestId: ${fileInfoResponse.requestId}`);
    } catch (error) {
      log(`Error getting file info: ${error}`);
    }

    // 5. List directory
    log(`\nListing directory: ${testDirPath}`);
    try {
      const listResponse = await session.fileSystem.listDirectory(testDirPath);
      log('Directory entries:');
      listResponse.entries.forEach((entry: FileEntry) => {
        log(`${entry.isDirectory ? '[DIR]' : '[FILE]'} ${entry.name}`);
      });
      log(`List Directory RequestId: ${listResponse.requestId}`);
    } catch (error) {
      log(`Error listing directory: ${error}`);
    }

    // 6. Edit file
    log(`\nEditing file: ${testFilePath}`);
    try {
      const edits = [
        {
          oldText: "second line",
          newText: "MODIFIED second line"
        }
      ];
      const editResponse = await session.fileSystem.editFile(testFilePath, edits, false);
      log(`File edited successfully: ${editResponse.success}`);
      log(`Edit File RequestId: ${editResponse.requestId}`);

      // Read the file again to verify the edit
      const readAgainResponse = await session.fileSystem.readFile(testFilePath);
      log(`Edited file content:\n${readAgainResponse.content}`);
      log(`Read File Again RequestId: ${readAgainResponse.requestId}`);
    } catch (error) {
      log(`Error editing file: ${error}`);
    }

    // 7. Search files
    log(`\nSearching for files in ${TestPathPrefix} containing 'sample'`);
    try {
      const searchResponse = await session.fileSystem.searchFiles(TestPathPrefix, "sample", undefined);
      log(`Search results: ${searchResponse.matches.length} files found`);
      searchResponse.matches.forEach((path: string) => {
        log(`- ${path}`);
      });
      log(`Search Files RequestId: ${searchResponse.requestId}`);
    } catch (error) {
      log(`Error searching files: ${error}`);
    }

    // 8. Move/Rename file
    const newFilePath = `${TestPathPrefix}/test_directory/renamed.txt`;
    log(`\nMoving file from ${testFilePath} to ${newFilePath}`);
    try {
      const moveResponse = await session.fileSystem.moveFile(testFilePath, newFilePath);
      log(`File moved successfully: ${moveResponse.success}`);
      log(`Move File RequestId: ${moveResponse.requestId}`);

      // List directory again to verify the move
      const listAgainResponse = await session.fileSystem.listDirectory(testDirPath);
      log('Directory entries after move:');
      listAgainResponse.entries.forEach((entry: FileEntry) => {
        log(`${entry.isDirectory ? '[DIR]' : '[FILE]'} ${entry.name}`);
      });
      log(`List Directory Again RequestId: ${listAgainResponse.requestId}`);
    } catch (error) {
      log(`Error moving file: ${error}`);
    }
  } finally {
    // Clean up by deleting the session when we're done
    log('\nDeleting the session...');
    try {
      const deleteResponse = await agentBay.delete(session);
      log('Session deleted successfully');
      log(`Delete Session RequestId: ${deleteResponse.requestId}`);
    } catch (error) {
      log(`Error deleting session: ${error}`);
    }
  }
}

main().catch(error => {
  logError('Error in main execution:', error);
  process.exit(1);
});
