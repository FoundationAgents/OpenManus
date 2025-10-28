import { log } from 'console';
import { AgentBay } from '../../src';
import { Session } from '../../src/session';

describe('File Operations Integration Tests', () => {
  let agentBay: AgentBay;
  let session: Session;

  beforeAll(async () => {
    // Step 1: Environment preparation
    agentBay = new AgentBay();
    expect(agentBay).toBeDefined();

    // Step 2: Session creation
    const sessionResult = await agentBay.create({
      imageId: 'linux_latest'
    });
    expect(sessionResult.success).toBe(true);
    expect(sessionResult.session).toBeDefined();

    session = sessionResult.session!;
    expect(session.getSessionId()).toBeDefined();
  });

  describe('File System CRUD Operations', () => {
    it('should perform complete file system operations workflow', async () => {
      // Step 3: File system retrieval
      const fileSystem = session.fileSystem;
      expect(fileSystem).toBeDefined();

      // Step 4: Directory creation
      const createDirResult = await fileSystem.createDirectory('/tmp/user');
      expect(createDirResult.success).toBe(true);

      // Step 5: Directory listing
      const listResult = await fileSystem.listDirectory('/tmp');
      expect(listResult.success).toBe(true);
      expect(listResult.entries).toBeDefined();
      expect(Array.isArray(listResult.entries)).toBe(true);
      expect(listResult.entries.length).toBeGreaterThan(0);
      for (const entry of listResult.entries) {
        if(entry.name === 'user') {
          expect(entry.isDirectory).toBe(true);
        }
      }

      const userDir = listResult.entries.find(entry => entry.name === 'user');
      expect(userDir).toBeDefined();
      expect(userDir?.isDirectory).toBe(true);

      // Step 6: File writing
      const testContent = 'hello world!!!';
      const writeResult = await fileSystem.writeFile('/tmp/user/test.txt', testContent, 'create_new');
      expect(writeResult.success).toBe(true);

      // Step 7: File reading
      const readResult = await fileSystem.readFile('/tmp/user/test.txt');
      expect(readResult.success).toBe(true);
      expect(readResult.content).toBe(testContent);

      // Step 8: File editing
      const edits = [{
        oldText: 'hello world!!!',
        newText: 'This line has been edited.'
      }];
      const editResult = await fileSystem.editFile('/tmp/user/test.txt', edits);
      expect(editResult.success).toBe(true);

      // Verify edit
      const editedResult = await fileSystem.readFile('/tmp/user/test.txt');
      expect(editedResult.success).toBe(true);
      expect(editedResult.content).toBe('This line has been edited.');

      // Step 9: File info retrieval
      const fileInfoResult = await fileSystem.getFileInfo('/tmp/user/test.txt');
      expect(fileInfoResult.success).toBe(true);
      log(JSON.stringify(fileInfoResult.fileInfo))
      expect(fileInfoResult.fileInfo).toBeDefined();
      expect(fileInfoResult.fileInfo!.size).toBeGreaterThan(0);
      // expect(fileInfoResult.fileInfo!.name).toBe('test.txt');

      // Step 10: Large file writing (62KB, automatic chunking)
      const largeContent = 'Lorem ipsum dolor sit amet, consectetur adipiscing elit. '.repeat(1134); // Approximately 62KB
      expect(largeContent.length).toBeGreaterThan(60000);

      const writeLargeResult = await fileSystem.writeFile('/tmp/user/large_context.txt', largeContent);
      log(`Write large file result: ${JSON.stringify(writeLargeResult)}`);
      expect(writeLargeResult.success).toBe(true);

      // Step 11: Large file reading (automatic chunking)
      const largeReadResult = await fileSystem.readFile('/tmp/user/large_context.txt');
      expect(largeReadResult.success).toBe(true);
      expect(largeReadResult.content).toBe(largeContent);
      expect(largeReadResult.content.length).toBeGreaterThan(60000);

      // Step 12: File moving
      const moveResult = await fileSystem.moveFile('/tmp/user/test.txt', '/tmp/test.txt');
      expect(moveResult.success).toBe(true);

      // Verify move operation
      const sourceReadResult = await fileSystem.readFile('/tmp/user/test.txt');
      expect(sourceReadResult.success).toBe(false);

      const movedReadResult = await fileSystem.readFile('/tmp/test.txt');
      expect(movedReadResult.success).toBe(true);
      expect(movedReadResult.content).toBe('This line has been edited.');

      // Step 13: Multiple files reading
      const multipleFiles = ['/tmp/user/large_context.txt', '/tmp/test.txt'];
      const multipleResults = await fileSystem.readMultipleFiles(multipleFiles);
      expect(multipleResults.success).toBe(true);
      expect(multipleResults.contents).toBeDefined();
      expect(typeof multipleResults.contents).toBe('object');
      expect(Object.keys(multipleResults.contents).length).toBe(2);

      // Step 14: Command executor retrieval
      const command = session.command;
      expect(command).toBeDefined();

      // Step 15: File deletion via command
      const deleteResult = await command.executeCommand('rm /tmp/test.txt');
      expect(deleteResult.success).toBe(true);

      // Step 16: File search verification
      const searchResults = await fileSystem.searchFiles('/tmp','test.txt', );
      log(`Search results: ${JSON.stringify(searchResults)}`);
      expect(searchResults.success).toBe(true);
      expect(searchResults.matches[0]).toContain('No matches found');

      // Verify test.txt is not in results
      const deletedFile = searchResults.matches.find(file => file.includes('test.txt'));
      expect(deletedFile).toBeUndefined();
      const searchLargeResults = await fileSystem.searchFiles('/tmp','large_context.txt', );
      // Verify large_context.txt is still there
      const largeFile = searchLargeResults.matches.find(file => file.includes('large_context.txt'));
      log(`Large file search result: ${JSON.stringify(largeFile)}`);
      expect(largeFile).toContain('large_context.txt');

    });

    it('should handle edge cases and special conditions', async () => {
      const fileSystem = session.fileSystem;
      const createDirResult = await fileSystem.createDirectory('/tmp/user');
      expect(createDirResult.success).toBe(true);

      // Edge case: Empty file creation and reading
      const writeEmptyResult = await fileSystem.writeFile('/tmp/user/empty.txt', '', 'create_new');
      log(`Write empty file result: ${JSON.stringify(writeEmptyResult)}`);
      expect(writeEmptyResult.success).toBe(true);

      const emptyReadResult = await fileSystem.readFile('/tmp/user/empty.txt');
      expect(emptyReadResult.success).toBe(true);
      expect(emptyReadResult.content).toBe('');

      // Edge case: File with special characters in name
      const specialFileName = '/tmp/user/special-filename-test@#$.txt';
      const specialContent = 'Content with Chinese and special chars: !@#$%^&*()';

      const writeSpecialResult = await fileSystem.writeFile(specialFileName, specialContent, 'create_new');
      expect(writeSpecialResult.success).toBe(true);

      const specialReadResult = await fileSystem.readFile(specialFileName);
      expect(specialReadResult.success).toBe(true);
      expect(specialReadResult.content).toBe(specialContent);

      // Edge case: Deep directory structure
      const createDeepDirResult = await fileSystem.createDirectory('/tmp/user/deep/nested/structure');
      expect(createDeepDirResult.success).toBe(true);

      const writeDeepResult = await fileSystem.writeFile('/tmp/user/deep/nested/structure/deep.txt', 'deep content', 'create_new');
      expect(writeDeepResult.success).toBe(true);

      const deepReadResult = await fileSystem.readFile('/tmp/user/deep/nested/structure/deep.txt');
      expect(deepReadResult.success).toBe(true);
      expect(deepReadResult.content).toBe('deep content');

    });
  });

    describe('Batch File Operations', () => {
      it.only('should read multiple files correctly', async () => {
        const files = ['/tmp/batch1.txt', '/tmp/batch2.txt', '/tmp/batch3.txt'];
        await session.fileSystem.writeFile(files[0], 'Content 1', 'overwrite');
        await session.fileSystem.writeFile(files[1], '', 'overwrite');
        await session.fileSystem.writeFile(files[2], 'Content 3', 'overwrite');

        const result = await session.fileSystem.readMultipleFiles(files);
        expect(result.success).toBe(true);
        expect(result.contents[files[0]]).toBe('Content 1');
        expect(result.contents[files[1]]).toBe('');
        expect(result.contents[files[2]]).toBe('Content 3');
      });

      it.only('should search files correctly', async () => {
        await session.fileSystem.createDirectory('/tmp/search_test');
        await session.fileSystem.writeFile('/tmp/search_test/test1.txt', 'content', 'overwrite');
        await session.fileSystem.writeFile('/tmp/search_test/test2.log', 'log', 'overwrite');

        const result1 = await session.fileSystem.searchFiles('/tmp/search_test', 'test1.txt');
        expect(result1.success).toBe(true);
        expect(result1.matches).toBeDefined();
        const result2 = await session.fileSystem.searchFiles('/tmp/search_test', "", ['test2.log']);
        expect(result2.success).toBe(true);
        expect(result2.matches).toBeDefined();
      });
    });

  afterAll(async () => {
    // Step 17: Resource cleanup
    if (session) {
      const deleteResult = await agentBay.delete(session);
      expect(deleteResult.success).toBe(true);
    }
  });
});
