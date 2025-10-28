/*
Command templates for various AgentBay operations.

This module contains shell command templates used by different modules
to execute operations in remote environments.

Template naming convention:
- Use descriptive names that clearly indicate the operation
- Group templates by functionality (mobile, desktop, network, etc.)
- Use consistent parameter naming across similar templates

Parameter conventions:
- Use snake_case for parameter names
- Include descriptive parameter names (e.g., lock_switch, package_list)
- Document expected parameter types and values
*/
package command

// ================================
// Mobile Device Command Templates
// ================================

// Resolution lock template
// Parameters:
//
//	lock_switch (string): "1" to enable lock, "0" to disable lock
const ResolutionLockTemplate = "setprop sys.wuying.lockres {lock_switch}"

// Application whitelist template
// Parameters:
//
//	package_list (string): Newline-separated list of package names
const AppWhitelistTemplate = `cat > /data/system/pm_whitelist.txt << 'EOF'
{package_list}
EOF
chmod 644 /data/system/pm_whitelist.txt
setprop rw.wy.pm_whitelist.refresh 1
setprop persist.wy.pm_blacklist.switch 2`

// Application blacklist template
// Parameters:
//
//	package_list (string): Newline-separated list of package names
const AppBlacklistTemplate = `cat > /data/system/pm_blacklist.txt << 'EOF'
{package_list}
EOF
chmod 644 /data/system/pm_blacklist.txt
setprop rw.wy.pm_blacklist.refresh 1
setprop persist.wy.pm_blacklist.switch 1`

// MobileCommandTemplates contains mobile command templates for easy access
var MobileCommandTemplates = map[string]string{
	"resolution_lock_enable":  "setprop sys.wuying.lockres 1",
	"resolution_lock_disable": "setprop sys.wuying.lockres 0",
	"app_whitelist":           AppWhitelistTemplate,
	"app_blacklist":           AppBlacklistTemplate,
}

// GetMobileCommandTemplate returns a mobile command template by name
func GetMobileCommandTemplate(templateName string) (string, bool) {
	template, exists := MobileCommandTemplates[templateName]
	return template, exists
}
