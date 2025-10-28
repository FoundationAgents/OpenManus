#!/usr/bin/env node

/**
 * AgentBay SDK - Data Persistence Example
 *
 * This example demonstrates real data persistence functionality:
 * - Context creation for persistent storage
 * - File persistence across multiple sessions
 * - Context synchronization and file sharing
 */

import type { CreateSessionParams } from '../../../src/agent-bay';
import { AgentBay, ContextSync, logError, newSyncPolicy } from '../../../src/index';

async function main(): Promise<void> {
    console.log('🗄️ AgentBay Data Persistence Example');
    
    // Initialize AgentBay client
    const apiKey = process.env.AGENTBAY_API_KEY || '';
    if (!apiKey) {
        console.log('❌ Please set AGENTBAY_API_KEY environment variable');
        process.exit(1);
    }
    
    const agentBay = new AgentBay({ apiKey });
    
    try {
        // Run the complete data persistence demonstration
        await dataPersistenceDemo(agentBay);
        
    } catch (error) {
        console.log(`❌ Example execution failed: ${error}`);
        logError('Error:', error);
    }
    
    console.log('✅ Data persistence example completed');
}

async function dataPersistenceDemo(agentBay: AgentBay): Promise<void> {
    console.log('\n🔄 === Data Persistence Demonstration ===');
    
    // Step 1: Create a context for persistent storage
    console.log('\n📦 Step 1: Creating context for persistent storage...');
    const contextResult = await agentBay.context.get('persistence-demo', true);
    
    if (!contextResult.success) {
        console.log(`❌ Context creation failed: ${contextResult.errorMessage}`);
        return;
    }
    
    const context = contextResult.context;
    console.log(`✅ Context created successfully: ${context.id}`);
    console.log(`   Name: ${context.name}`);
    console.log(`   State: ${context.state}`);
    
    // Step 2: Create first session with context sync
    console.log('\n🔧 Step 2: Creating first session with context synchronization...');
    
    // Create sync policy for context synchronization
    const syncPolicy = newSyncPolicy();
    
    // Create context sync configuration
    const contextSync = new ContextSync(
        context.id,
        '/tmp/persistent_data',  // Mount context to this path in session
        syncPolicy
    );
    
    // Create session with context sync
    const params1: CreateSessionParams = {
        contextSync: [contextSync]
    };
    const session1Result = await agentBay.create(params1);
    
    if (!session1Result.success) {
        console.log(`❌ First session creation failed: ${session1Result.errorMessage}`);
        return;
    }
    
    const session1 = session1Result.session;
    console.log(`✅ First session created successfully: ${session1.sessionId}`);
    
    let session1Id = '';
    try {
        session1Id = session1.sessionId;
        
        // Step 3: Write persistent data in first session
        console.log('\n💾 Step 3: Writing persistent data in first session...');
        
        // Create directory structure
        await session1.command.executeCommand('mkdir -p /tmp/persistent_data/config');
        await session1.command.executeCommand('mkdir -p /tmp/persistent_data/logs');
        
        // Write configuration file
        const configData = {
            app_name: 'AgentBay Demo',
            version: '1.0.0',
            created_at: new Date().toISOString(),
            session_id: session1.sessionId,
            features: ['data_persistence', 'context_sync', 'multi_session']
        };
        const configContent = JSON.stringify(configData, null, 2);
        
        const configResult = await session1.fileSystem.writeFile('/tmp/persistent_data/config/app.json', configContent);
        if (configResult.success) {
            console.log('✅ Configuration file written successfully');
        } else {
            console.log(`❌ Failed to write config file: ${configResult.errorMessage}`);
        }
        
        // Write a log file
        const logContent = `Application Log - Session 1
Created: ${new Date().toISOString()}
Session ID: ${session1.sessionId}
Operation: Data persistence demonstration
Status: Files created successfully
`;
        
        const logResult = await session1.fileSystem.writeFile('/tmp/persistent_data/logs/session1.log', logContent);
        if (logResult.success) {
            console.log('✅ Log file written successfully');
        } else {
            console.log(`❌ Failed to write log file: ${logResult.errorMessage}`);
        }
        
        // Write a data file
        const dataContent = 'This is persistent data that should be available across sessions.\nIt demonstrates the context synchronization functionality.';
        
        const dataResult = await session1.fileSystem.writeFile('/tmp/persistent_data/shared_data.txt', dataContent);
        if (dataResult.success) {
            console.log('✅ Data file written successfully');
        } else {
            console.log(`❌ Failed to write data file: ${dataResult.errorMessage}`);
        }
        
        // List files to verify
        console.log('\n📋 Files created in first session:');
        const listResult = await session1.command.executeCommand('find /tmp/persistent_data -type f -ls');
        if (listResult.success) {
            console.log(listResult.output);
        }

        
    } finally {
        // Clean up first session
        console.log('\n🧹 Cleaning up first session...');
        const deleteResult1 = await agentBay.delete(session1, true);  // Sync before deletion
        if (deleteResult1.success) {
            console.log('✅ First session deleted successfully (with context sync)');
        } else {
            console.log(`❌ First session deletion failed: ${deleteResult1.errorMessage}`);
        }
    }
    
    // Step 4: Create second session to verify persistence
    console.log('\n🔧 Step 4: Creating second session to verify data persistence...');
    
    // Create second session with same context sync
    const params2: CreateSessionParams = {
        contextSync: [contextSync]
    };
    const session2Result = await agentBay.create(params2);
    
    if (!session2Result.success) {
        console.log(`❌ Second session creation failed: ${session2Result.errorMessage}`);
        return;
    }
    
    const session2 = session2Result.session;
    console.log(`✅ Second session created successfully: ${session2.sessionId}`);
    
    try {
        // Step 5: Verify persistent data in second session
        console.log('\n🔍 Step 5: Verifying persistent data in second session...');
        
        // Note: agent_bay.create() already waits for context synchronization to complete
        console.log('✅ Context synchronization completed (handled by agentBay.create())');
        
        // Check if files exist
        const filesToCheck = [
            '/tmp/persistent_data/config/app.json',
            '/tmp/persistent_data/logs/session1.log', 
            '/tmp/persistent_data/shared_data.txt'
        ];
        
        let persistentFilesFound = 0;
        
        for (const filePath of filesToCheck) {
            console.log(`\n🔍 Checking file: ${filePath}`);
            const readResult = await session2.fileSystem.readFile(filePath);
            
            if (readResult.success) {
                console.log('✅ File found and readable!');
                if (filePath.endsWith('.json')) {
                    try {
                        const data = JSON.parse(readResult.content);
                        console.log(`   📄 Config data: ${data.app_name} v${data.version}`);
                        console.log(`   🕒 Created by session: ${data.session_id}`);
                    } catch {
                        console.log(`   📄 Content: ${readResult.content.substring(0, 100)}...`);
                    }
                } else {
                    console.log(`   📄 Content preview: ${readResult.content.substring(0, 100)}...`);
                }
                persistentFilesFound++;
            } else {
                console.log(`❌ File not found or not readable: ${readResult.errorMessage}`);
            }
        }
        
        // Add new data in second session
        console.log('\n💾 Adding new data in second session...');
        const session2Log = `Application Log - Session 2
Created: ${new Date().toISOString()}
Session ID: ${session2.sessionId}
Operation: Data persistence verification
Persistent files found: ${persistentFilesFound}/${filesToCheck.length}
Status: Persistence verification completed
`;
        
        const session2Result = await session2.fileSystem.writeFile('/tmp/persistent_data/logs/session2.log', session2Log);
        if (session2Result.success) {
            console.log('✅ Second session log written successfully');
        }
        
        // Summary
        console.log('\n📊 === Persistence Verification Summary ===');
        console.log(`✅ Context ID: ${context.id}`);
        console.log(`✅ First session: ${session1Id} (deleted)`);
        console.log(`✅ Second session: ${session2.sessionId} (active)`);
        console.log(`✅ Persistent files found: ${persistentFilesFound}/${filesToCheck.length}`);
        
        if (persistentFilesFound === filesToCheck.length) {
            console.log('🎉 Data persistence verification SUCCESSFUL!');
            console.log('   Files created in first session are accessible in second session');
        } else {
            console.log('⚠️  Data persistence verification PARTIAL');
            console.log('   Some files may still be syncing or failed to persist');
        }
        
    } finally {
        // Clean up second session
        console.log('\n🧹 Cleaning up second session...');
        const deleteResult2 = await agentBay.delete(session2, true);
        if (deleteResult2.success) {
            console.log('✅ Second session deleted successfully (with context sync)');
        } else {
            console.log(`❌ Second session deletion failed: ${deleteResult2.errorMessage}`);
        }
    }
}


// Execute the main function
if (require.main === module) {
    main().catch(error => {
        logError('Error in main execution:', error);
        process.exit(1);
    });
}