/**
 * AgentBay SDK - Automation Features Example (TypeScript)
 *
 * This example demonstrates how to use AgentBay SDK automation features, including:
 * - Command execution
 * - Code execution
 * - UI automation
 * - Workflow orchestration
 */

import { AgentBay,KeyCode } from 'wuying-agentbay-sdk';

async function main(): Promise<void> {
    console.log('🚀 AgentBay Automation Features Example (TypeScript)');

    // Initialize AgentBay client
    const agentBay = new AgentBay();

    // Create session
    console.log('\n📱 Creating session...');
    const sessionResult = await agentBay.create({imageId:'code_latest'});
    const mobileResult = await agentBay.create({imageId:'mobile_latest'})
    if (!sessionResult.success) {
        console.log(`❌ Session creation failed: ${sessionResult.errorMessage}`);
        return;
    }
    if (!mobileResult.success) {
        console.log(`❌ Session creation failed: ${mobileResult.errorMessage}`);
        return;
    }

    const session = sessionResult.session;
    const mobileSession = mobileResult.session;
    console.log(`✅ Session created successfully: ${session.sessionId}`);

    try {
        // 1. Command execution example
        await commandExecutionExample(session);

        // 2. Code execution example
        await codeExecutionExample(session);

        // 3. UI automation example
        await uiAutomationExample(mobileSession);

        // 4. Workflow orchestration example
        await workflowExample(mobileSession);

    } catch (error) {
        console.log(`❌ Example execution failed: ${error}`);
    } finally {
        // Clean up session
        console.log(`\n🧹 Cleaning up session: ${session.sessionId}`);
        await agentBay.delete(session);
        await agentBay.delete(mobileSession);
        console.log('✅ Example execution completed');
    }
}

async function commandExecutionExample(session: any): Promise<void> {
    console.log('\n💻 === Command Execution Example ===');

    // Basic command execution
    const commands = [
        'whoami',
        'pwd',
        'ls -la /tmp',
        'df -h',
        'free -h'
    ];

    for (const cmd of commands) {
        console.log(`\n🔄 Executing command: ${cmd}`);
        const result = await session.command.executeCommand(cmd);

        if (result.success) {
            console.log(`✅ Output: ${result.output.trim()}`);
        } else {
            console.log(`❌ Command failed: ${result.errorMessage}`);
        }
    }

    // Command execution with timeout
    console.log('\n🔄 Executing command with timeout...');
    const timeoutResult = await session.command.executeCommand('sleep 2', 5000);
    if (timeoutResult.success) {
        console.log('✅ Timeout command executed successfully');
    } else {
        console.log(`❌ Timeout command failed: ${timeoutResult.errorMessage}`);
    }
}

async function codeExecutionExample(session: any): Promise<void> {
    console.log('\n🐍 === Code Execution Example ===');

    // Python code execution
    const pythonCode = `
import sys
import os
import json
from datetime import datetime

# System information
system_info = {
    "python_version": sys.version,
    "current_directory": os.getcwd(),
    "timestamp": datetime.now().isoformat(),
    "environment_vars": len(os.environ)
}

print("Python code executed successfully!")
print(f"System info: {json.dumps(system_info, indent=2)}")

# Simple calculation
numbers = list(range(1, 11))
total = sum(numbers)
print(f"Sum of 1 to 10: {total}")
`;

    console.log('🔄 Executing Python code...');
    const pythonResult = await session.code.runCode(pythonCode, 'python');
    if (pythonResult.success) {
        console.log('✅ Python code executed successfully:');
        console.log(pythonResult.result);
    } else {
        console.log(`❌ Python code execution failed: ${pythonResult.errorMessage}`);
    }

    // JavaScript code execution
    const jsCode = `
console.log("JavaScript code executed successfully!");

// Get system information
const os = require('os');
const systemInfo = {
    platform: os.platform(),
    arch: os.arch(),
    nodeVersion: process.version,
    memory: Math.round(os.totalmem() / 1024 / 1024) + ' MB'
};

console.log("System info:", JSON.stringify(systemInfo, null, 2));

// Array operations
const numbers = [1, 2, 3, 4, 5];
const doubled = numbers.map(n => n * 2);
console.log("Original array:", numbers);
console.log("Doubled:", doubled);
`;

    console.log('\n🔄 Executing JavaScript code...');
    const jsResult = await session.code.runCode(jsCode, 'javascript');
    if (jsResult.success) {
        console.log('✅ JavaScript code executed successfully:');
        console.log(jsResult.result);
    } else {
        console.log(`❌ JavaScript code execution failed: ${jsResult.errorMessage}`);
    }
}

async function uiAutomationExample(session: any): Promise<void> {
    console.log('\n🖱️ === UI Automation Example ===');

    try {
        // Screenshot
        console.log('🔄 Taking screenshot...');
        const screenshot = await session.ui.screenshot();
        if (screenshot.success) {
            // Save screenshot
            await session.fileSystem.writeFile('/tmp/screenshot.png', screenshot.data);
            console.log('✅ Screenshot saved successfully: /tmp/screenshot.png');
        } else {
            console.log(`❌ Screenshot failed: ${screenshot.errorMessage}`);
        }

        // Simulate keyboard input
        console.log('🔄 Simulating keyboard input...');
        await session.ui.sendKey(KeyCode.HOME);
        console.log('✅ Keyboard input completed');

        // Simulate mouse operations
        console.log('🔄 Simulating mouse operations...');
        await session.ui.click({ x: 100, y: 100 });
        console.log('✅ Mouse click completed');

    } catch (error) {
        console.log(`⚠️ UI automation features may not be available: ${error}`);
    }
}

async function workflowExample(session: any): Promise<void> {
    console.log('\n🔄 === Workflow Orchestration Example ===');

    console.log('🔄 Executing data processing workflow...');

    // Step 1: Create test data
    console.log('Step 1: Creating test data...');
    const createDataCode = `
import json
import random
from datetime import datetime, timedelta

# Generate test data
data = []
base_date = datetime.now()

for i in range(50):
    record = {
        "id": i + 1,
        "name": f"User{i+1}",
        "score": random.randint(60, 100),
        "date": (base_date - timedelta(days=random.randint(0, 30))).isoformat(),
        "category": random.choice(["A", "B", "C"])
    }
    data.append(record)

# Save data
with open('/tmp/test_data.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print(f"Generated {len(data)} test records")
`;

    const createResult = await session.code.runCode(createDataCode, 'python');
    if (!createResult.success) {
        console.log(`❌ Data creation failed: ${createResult.errorMessage}`);
        return;
    }
    console.log('✅ Test data creation completed');

    // Step 2: Data analysis (using JavaScript)
    console.log('Step 2: Data analysis...');
    const analysisCode = `
const fs = require('fs');

// Read data
const rawData = fs.readFileSync('/tmp/test_data.json', 'utf8');
const data = JSON.parse(rawData);

// Analyze data
const scores = data.map(record => record.score);
const categories = {};
data.forEach(record => {
    const cat = record.category;
    categories[cat] = (categories[cat] || 0) + 1;
});

const analysisResult = {
    total_records: data.length,
    average_score: scores.reduce((a, b) => a + b, 0) / scores.length,
    max_score: Math.max(...scores),
    min_score: Math.min(...scores),
    category_distribution: categories
};

// Save analysis results
fs.writeFileSync('/tmp/analysis_result.json', JSON.stringify(analysisResult, null, 2));

console.log("Data analysis completed:");
Object.entries(analysisResult).forEach(([key, value]) => {
    console.log(\`  \${key}: \${JSON.stringify(value)}\`);
});
`;

    const analysisResult = await session.code.runCode(analysisCode, 'javascript');
    if (!analysisResult.success) {
        console.log(`❌ Data analysis failed: ${analysisResult.errorMessage}`);
        return;
    }
    console.log('✅ Data analysis completed');

    // Step 3: Generate report
    console.log('Step 3: Generating report...');
    const reportCode = `
import json
from datetime import datetime

# Read analysis results
with open('/tmp/analysis_result.json', 'r', encoding='utf-8') as f:
    analysis = json.load(f)

# Generate HTML report
html_report = f'''
<!DOCTYPE html>
<html>
<head>
    <title>Data Analysis Report</title>
    <meta charset="utf-8">
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; }}
        .header {{ background-color: #f0f8ff; padding: 20px; border-radius: 8px; }}
        .metric {{ margin: 10px 0; padding: 10px; background-color: #f9f9f9; border-radius: 5px; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Data Analysis Report (TypeScript Example)</h1>
        <p>Generated at: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
    </div>

    <div class="metric">
        <h3>Basic Statistics</h3>
        <p>Total records: {analysis['total_records']}</p>
        <p>Average score: {analysis['average_score']:.2f}</p>
        <p>Max score: {analysis['max_score']}</p>
        <p>Min score: {analysis['min_score']}</p>
    </div>

    <div class="metric">
        <h3>Category Distribution</h3>
'''

for category, count in analysis['category_distribution'].items():
    html_report += f'        <p>Category {category}: {count} records</p>\\n'

html_report += '''
    </div>
</body>
</html>
'''

# Save report
with open('/tmp/report.html', 'w', encoding='utf-8') as f:
    f.write(html_report)

print("HTML report generated: /tmp/report.html")
`;

    const reportResult = await session.code.runCode(reportCode, 'python');
    if (!reportResult.success) {
        console.log(`❌ Report generation failed: ${reportResult.errorMessage}`);
        return;
    }
    console.log('✅ Report generation completed');

    // Step 4: Verify results
    console.log('Step 4: Verifying results...');
    const filesToCheck = ['/tmp/test_data.json', '/tmp/analysis_result.json', '/tmp/report.html'];

    for (const filePath of filesToCheck) {
        const result = await session.fileSystem.readFile(filePath);
        if (result.success) {
            console.log(`✅ File exists: ${filePath} (${result.content.length} bytes)`);
        } else {
            console.log(`❌ File not found: ${filePath}`);
        }
    }

    console.log('🎉 Workflow execution completed!');
}

// Run example
if (require.main === module) {
    main().catch(console.error);
}

export { main };
