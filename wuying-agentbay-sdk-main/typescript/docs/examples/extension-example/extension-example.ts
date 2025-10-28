/**
 * Comprehensive Extension Management Example
 *
 * This example demonstrates how to use the TypeScript extension functionality
 * to manage browser extensions in the Wuying AgentBay SDK.
 *
 * Features demonstrated:
 * - Basic extension upload and management
 * - Multiple extensions handling
 * - Browser session integration
 * - Development workflow patterns
 * - Error handling and cleanup
 */

import { AgentBay, ExtensionsService, Extension, ExtensionOption, BrowserContext } from "wuying-agentbay-sdk";
import * as fs from "fs";

/**
 * Basic Extension Management Example
 * Demonstrates fundamental extension operations
 */
async function basicExtensionExample(): Promise<boolean> {
  console.log("🚀 Starting basic extension example...");

  // Initialize AgentBay client
  const agentBay = new AgentBay({
    apiKey: process.env.AGENTBAY_API_KEY || "your-api-key-here",
  });

  // Create extensions service with auto-generated context
  const extensionsService = new ExtensionsService(agentBay);

  try {
    // Example extension path (update with your actual extension)
    const extensionPath = "/path/to/your-extension.zip";

    if (!fs.existsSync(extensionPath)) {
      console.log(`❌ Extension file not found: ${extensionPath}`);
      console.log("💡 Please update the extensionPath variable with a valid ZIP file");
      console.log("📝 Continuing with simulated workflow...\n");
      return false;
    }

    // Upload extension to cloud
    console.log(`📦 Uploading extension: ${extensionPath}`);
    const extension = await extensionsService.create(extensionPath);
    console.log(`✅ Extension uploaded successfully!`);
    console.log(`   - Name: ${extension.name}`);
    console.log(`   - ID: ${extension.id}`);

    // Create extension option for browser session
    console.log("🔧 Creating extension configuration...");
    const extOption = extensionsService.createExtensionOption([extension.id]);
    console.log(`✅ Extension option created: ${extOption.toDisplayString()}`);

    // Create browser session with extension
    console.log("🌐 Creating browser session with extension...");

    // Create session parameters with browser context configuration
    // In a real implementation, you would use the BrowserContext class:
    // const browserContext = new BrowserContext("basic_extension_session", true, extOption);
    // For this example, we'll use a plain object to demonstrate the structure:
    const sessionParams = {
      labels: { purpose: "basic_extension_example", type: "demo" },
      browserContext: new BrowserContext("basic_extension_session",true,extOption)

    };

    const sessionResult = await agentBay.create(sessionParams);
    if (!sessionResult.success) {
      console.log(`❌ Failed to create session: ${sessionResult.errorMessage}`);
      return false;
    }

    const session = sessionResult.session;
    console.log(`✅ Browser session created successfully!`);
    console.log(`   - Session ID: ${session.sessionId}`);
    console.log(`   - Extensions synchronized to: /tmp/extensions/`);

    // List available extensions in context
    console.log("\n📋 Listing available extensions:");
    const extensions = await extensionsService.list();
    for (const ext of extensions) {
      console.log(`   - ${ext.name} (ID: ${ext.id})`);
    }

    console.log("\n🎉 Basic extension example completed successfully!");
    return true;

  } catch (error) {
    console.log(`❌ Error during basic extension example: ${error}`);
    return false;
  } finally {
    // Clean up resources
    console.log("\n🧹 Cleaning up resources...");
    await extensionsService.cleanup();
    console.log("✅ Cleanup completed\n");
  }
}

/**
 * Multiple Extensions Example
 * Demonstrates handling multiple extensions in a single session
 */
async function multipleExtensionsExample(): Promise<boolean> {
  console.log("🚀 Starting multiple extensions example...");

  const agentBay = new AgentBay({
    apiKey: process.env.AGENTBAY_API_KEY || "your-api-key-here",
  });
  const extensionsService = new ExtensionsService(agentBay, "multi_ext_demo");

  try {
    // List of extension paths (update with your actual extensions)
    const extensionPaths = [
      "/path/to/extension1.zip",
      "/path/to/extension2.zip",
      "/path/to/extension3.zip"
    ];

    // Filter existing files
    const existingPaths = extensionPaths.filter(path => fs.existsSync(path));
    if (existingPaths.length === 0) {
      console.log("❌ No extension files found. Please update extensionPaths with valid ZIP files");
      console.log("📝 Continuing with simulated workflow...\n");
      return false;
    }

    console.log(`📦 Uploading ${existingPaths.length} extensions...`);

    // Upload all extensions
    const extensionIds: string[] = [];
    for (const path of existingPaths) {
      const ext = await extensionsService.create(path);
      extensionIds.push(ext.id);
      console.log(`   ✅ ${ext.name} uploaded (ID: ${ext.id})`);
    }

    // Create session with all extensions
    console.log("🔧 Creating configuration for all extensions...");
    const extOption = extensionsService.createExtensionOption(extensionIds);

    // Create session parameters with browser context configuration
    // In a real implementation, you would use the BrowserContext class:
    // const browserContext = new BrowserContext("multi_extension_session", true, extOption);
    // For this example, we'll use a plain object to demonstrate the structure:
    const sessionParams = {
      labels: {
        purpose: "multiple_extensions",
        count: extensionIds.length.toString()
      },
      browserContext: new BrowserContext("multi_extension_session",true,extOption)

    };

    console.log("🌐 Creating browser session...");
    const sessionResult = await agentBay.create(sessionParams);
    const session = sessionResult.session;

    console.log(`✅ Session created with ${extensionIds.length} extensions!`);
    console.log(`   - Session ID: ${session.sessionId}`);

    console.log("\n🎉 Multiple extensions example completed successfully!");
    return true;

  } catch (error) {
    console.log(`❌ Error: ${error}`);
    return false;
  } finally {
    await extensionsService.cleanup();
    console.log("✅ Multiple extensions cleanup completed\n");
  }
}

/**
 * Extension Development Workflow Example
 * Demonstrates a complete development and testing workflow
 */
async function extensionDevelopmentWorkflow(): Promise<boolean> {
  console.log("🚀 Starting extension development workflow...");

  const agentBay = new AgentBay({
    apiKey: process.env.AGENTBAY_API_KEY || "your-api-key-here",
  });
  const extensionsService = new ExtensionsService(agentBay, "dev_workflow");

  try {
    // Step 1: Upload initial extension
    const initialExtensionPath = "/path/to/initial-extension.zip";
    if (!fs.existsSync(initialExtensionPath)) {
      console.log("❌ Initial extension file not found. Using simulated workflow.");
      console.log("📝 In a real scenario, you would:");
      console.log("   1. Upload your extension ZIP file");
      console.log("   2. Create a test session with the extension");
      console.log("   3. Test extension functionality");
      console.log("   4. Update extension if needed");
      console.log("   5. Deploy to production\n");
      return false;
    }

    console.log("📦 Step 1: Upload initial extension");
    const extension = await extensionsService.create(initialExtensionPath);
    console.log(`✅ Initial extension uploaded: ${extension.id}`);

    // Step 2: Test with browser session
    console.log("🌐 Step 2: Create test session");
    const extOption = extensionsService.createExtensionOption([extension.id]);

    // Create session parameters with browser context configuration
    // In a real implementation, you would use the BrowserContext class:
    // const browserContext = new BrowserContext("dev_test_session", true, extOption);
    // For this example, we'll use a plain object to demonstrate the structure:
    const sessionParams = {
      labels: { purpose: "development", phase: "testing" },
      browserContext: new BrowserContext("dev_test_session",true,extOption)
    };

    const sessionResult = await agentBay.create(sessionParams);
    const session = sessionResult.session;
    console.log(`✅ Test session created: ${session.sessionId}`);

    // Step 3: Update extension (simulated)
    console.log("🔄 Step 3: Update extension (simulated)");
    const updatedExtensionPath = "/path/to/updated-extension.zip";
    if (fs.existsSync(updatedExtensionPath)) {
      const updatedExtension = await extensionsService.update(extension.id, updatedExtensionPath);
      console.log(`✅ Extension updated: ${updatedExtension.name}`);
    } else {
      console.log("⚠ Updated extension file not found, skipping update step");
    }

    // Step 4: List all extensions in development context
    console.log("📋 Step 4: Review all extensions in development");
    const allExtensions = await extensionsService.list();
    allExtensions.forEach((ext, index) => {
      console.log(`   ${index + 1}. ${ext.name} (ID: ${ext.id})`);
    });

    console.log("\n🎉 Extension development workflow completed successfully!");
    return true;

  } catch (error) {
    console.log(`❌ Error in development workflow: ${error}`);
    return false;
  } finally {
    await extensionsService.cleanup();
    console.log("✅ Development workflow cleanup completed\n");
  }
}

/**
 * Error Handling and Validation Example
 * Demonstrates proper error handling patterns
 */
function errorHandlingExample(): void {
  console.log("🚀 Starting error handling example...");

  try {
    // This will throw an error - empty context ID
    const invalidOption1 = new ExtensionOption("", ["ext_1"]);
  } catch (error) {
    console.log(`✅ Caught expected error: ${error instanceof Error ? error.message : String(error)}`);
  }

  try {
    // This will also throw an error - empty extension IDs
    const invalidOption2 = new ExtensionOption("valid-context", []);
  } catch (error) {
    console.log(`✅ Caught expected error: ${error instanceof Error ? error.message : String(error)}`);
  }

  // Valid configuration
  const validOption = new ExtensionOption("valid-context", ["ext_1", "ext_2"]);
  console.log(`✅ Valid option created: ${validOption.toDisplayString()}`);
  console.log(`✅ Validation result: ${validOption.validate()}`);

  console.log("\n🎉 Error handling example completed!\n");
}

/**
 * Main execution function that runs all examples
 */
async function extensionManagementExample(): Promise<void> {
  console.log("=== Comprehensive Extension Management Examples ===\n");

  // Check API key
  if (!process.env.AGENTBAY_API_KEY) {
    console.log("❌ Please set AGENTBAY_API_KEY environment variable");
    console.log("💡 Example: export AGENTBAY_API_KEY='your-api-key-here'\n");
  }

  try {
    // Run all examples
    console.log("1. Basic Extension Example");
    console.log("-".repeat(40));
    await basicExtensionExample();

    console.log("2. Multiple Extensions Example");
    console.log("-".repeat(40));
    await multipleExtensionsExample();

    console.log("3. Extension Development Workflow");
    console.log("-".repeat(40));
    await extensionDevelopmentWorkflow();

    console.log("4. Error Handling Example");
    console.log("-".repeat(40));
    errorHandlingExample();

    console.log("=== All Extension Examples Completed Successfully! ===\n");

    console.log("💡 Next steps:");
    console.log("   - Update extension paths with your actual ZIP files");
    console.log("   - Set AGENTBAY_API_KEY environment variable");
    console.log("   - Check the API documentation for advanced usage");
    console.log("   - Explore browser automation integration patterns");

  } catch (error) {
    console.error("❌ Extension management examples failed:", error);
    throw error;
  }
}

// Helper function to demonstrate batch extension creation
async function batchExtensionCreation(extensionsService: ExtensionsService, paths: string[]): Promise<Extension[]> {
  const extensions: Extension[] = [];

  for (const path of paths) {
    try {
      if (fs.existsSync(path)) {
        const extension = await extensionsService.create(path);
        extensions.push(extension);
        console.log(`Created extension: ${extension.name}`);
      } else {
        console.log(`Skipping ${path}: File not found`);
      }
    } catch (error) {
      console.error(`Failed to create extension from ${path}:`, error);
    }
  }

  return extensions;
}

// Helper function to demonstrate extension validation
function validateExtensionOption(option: ExtensionOption): void {
  console.log(`Validating extension option: ${option.toDisplayString()}`);

  if (option.validate()) {
    console.log("✅ Extension option is valid");
    console.log(`  Context ID: ${option.contextId}`);
    console.log(`  Extension count: ${option.extensionIds.length}`);
    console.log(`  Extension IDs: ${option.extensionIds.join(', ')}`);
  } else {
    console.log("❌ Extension option is invalid");
  }
}

// Run the example if this file is executed directly
if (require.main === module) {
  extensionManagementExample()
    .then(() => {
      console.log("Extension examples completed successfully!");
      process.exit(0);
    })
    .catch((error) => {
      console.error("Extension examples failed:", error);
      process.exit(1);
    });
}

export {
  extensionManagementExample,
  basicExtensionExample,
  multipleExtensionsExample,
  extensionDevelopmentWorkflow,
  errorHandlingExample,
  batchExtensionCreation,
  validateExtensionOption,
};
