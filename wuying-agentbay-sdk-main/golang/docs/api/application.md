# Application Class

> **⚠️ DEPRECATED**: This API is deprecated. Please use the [Computer API](computer.md) instead for application management functionality.

The Application class provides methods for managing applications in the AgentBay cloud environment, including listing installed applications, starting applications, and stopping running processes.

## Overview

The Application class is accessed through a session instance and provides methods for application management in the cloud environment.

## Data Types


Represents an installed application.


```go
type InstalledApp struct {
    Name          string `json:"name"`
    StartCmd      string `json:"start_cmd"`
    StopCmd       string `json:"stop_cmd,omitempty"`
    WorkDirectory string `json:"work_directory,omitempty"`
}
```


Represents a running process.


```go
type Process struct {
    PName   string `json:"pname"`
    PID     int    `json:"pid"`
    CmdLine string `json:"cmdline,omitempty"`
}
```

## Methods


Retrieves a list of installed applications.


```go
func (am *ApplicationManager) GetInstalledApps(includeSystemApps bool, includeStoreApps bool, includeDesktopApps bool) (*InstalledAppsResult, error)
```

**Parameters:**
- `includeSystemApps` (bool): Whether to include system applications.
- `includeStoreApps` (bool): Whether to include store applications.
- `includeDesktopApps` (bool): Whether to include desktop applications.

**Returns:**
- `*InstalledAppsResult`: A result object containing the list of installed applications and RequestID.
- `error`: An error if the operation fails.

**InstalledAppsResult Structure:**
```go
type InstalledAppsResult struct {
    RequestID string         // Unique request identifier for debugging
    Apps      []*InstalledApp // Array of installed applications
}

type InstalledApp struct {
    Name        string // Application name
    Path        string // Application path
    Version     string // Application version
    Description string // Application description
}
```


Starts an application with the given command and optional working directory.


```go
func (am *ApplicationManager) StartApp(startCmd string, workDirectory string) (string, error)
```

**Parameters:**
- `startCmd` (string): The command used to start the application.
- `workDirectory` (string): The working directory for the application.

**Returns:**
- `string`: A JSON string containing the list of processes started.
- `error`: An error if the operation fails.


Stops an application by process name.


```go
func (am *ApplicationManager) StopAppByPName(pname string) (string, error)
```

**Parameters:**
- `pname` (string): The name of the process to stop.

**Returns:**
- `string`: A success message if the operation was successful.
- `error`: An error if the operation fails.


Stops an application by process ID.


```go
func (am *ApplicationManager) StopAppByPID(pid int) (string, error)
```

**Parameters:**
- `pid` (int): The process ID to stop.

**Returns:**
- `string`: A success message if the operation was successful.
- `error`: An error if the operation fails.


Stops an application by stop command.


```go
func (am *ApplicationManager) StopAppByCmd(stopCmd string) (string, error)
```

**Parameters:**
- `stopCmd` (string): The command used to stop the application.

**Returns:**
- `string`: A success message if the operation was successful.
- `error`: An error if the operation fails.


Lists all currently visible applications.


```go
func (am *ApplicationManager) ListVisibleApps() (*VisibleAppsResult, error)
```

**Returns:**
- `*VisibleAppsResult`: A result object containing the list of visible processes and RequestID.
- `error`: An error if the operation fails.

**VisibleAppsResult Structure:**
```go
type VisibleAppsResult struct {
    RequestID string     // Unique request identifier for debugging
    Processes []*Process // Array of visible processes
}

type Process struct {
    PName string // Process name
    PID   int    // Process ID
}
```

## Usage Examples

### Application Management

```go
package main

import (
    "fmt"
    "log"
)

func main() {
    // Create a session
    agentBay := agentbay.NewAgentBay("your-api-key")
    sessionResult, err := agentBay.Create(nil)
    if err != nil {
        log.Fatal(err)
    }
    session := sessionResult.Session

    // Get installed applications
    appsResult, err := session.Application.GetInstalledApps(true, false, true)
    if err != nil {
        log.Printf("Error getting installed apps: %v", err)
    } else {
        for _, app := range appsResult.Applications {
            fmt.Printf("Application: %s\n", app.Name)
        }
    }

    // Start an application
    processesResult, err := session.Application.StartApp("/usr/bin/google-chrome-stable")
    if err != nil {
        log.Printf("Error starting app: %v", err)
    } else {
        for _, process := range processesResult.Processes {
            fmt.Printf("Started process: %s (PID: %d)\n", process.PName, process.PID)
        }
    }

    // List visible applications
    visibleResult, err := session.Application.ListVisibleApps()
    if err != nil {
        log.Printf("Error listing visible apps: %v", err)
    } else {
        for _, app := range visibleResult.Processes {
            fmt.Printf("Visible application: %s (PID: %d)\n", app.PName, app.PID)
        }
    }

    // Stop an application by PID
    if len(processesResult.Processes) > 0 {
        success, err := session.Application.StopAppByPID(processesResult.Processes[0].PID)
        if err != nil {
            log.Printf("Error stopping app: %v", err)
        } else {
            fmt.Printf("Application stopped: %s\n", success)
        }
    }
}
```

## Related Resources

- [Session Class](session.md): The session class that provides access to the Application class.
- [Window Class](window.md): The window class for managing windows in the cloud environment.
- [Applications Concept](../concepts/applications.md): Conceptual information about applications in the AgentBay cloud environment. 