# Application Class

> **⚠️ DEPRECATED**: This API is deprecated. Please use the [Computer API](computer.md) instead for application management functionality.

The Application class provides methods for managing applications in the AgentBay cloud environment, including listing installed applications, starting applications, and stopping running processes.

## Overview

The Application class is accessed through a session instance and provides methods for application management in the cloud environment.

## Data Types


Represents an installed application.


```typescript
interface InstalledApp {
    name: string;       // The name of the application
    start_cmd: string;  // The command used to start the application
    stop_cmd?: string;  // The command used to stop the application (optional)
    work_directory?: string; // The working directory for the application (optional)
}
```


```typescript
interface Process {
    pname: string;   // The name of the process
    pid: number;     // The process ID
    cmdline?: string; // The command line used to start the process (optional)
}
```


```typescript
async getInstalledApps(includeSystemApps: boolean = true, includeStoreApps: boolean = false, includeDesktopApps: boolean = true): Promise<InstalledApp[]>
```

**Parameters:**
- `includeSystemApps` (boolean, optional): Whether to include system applications. Default is true.
- `includeStoreApps` (boolean, optional): Whether to include store applications. Default is false.
- `includeDesktopApps` (boolean, optional): Whether to include desktop applications. Default is true.

**Returns:**
- `Promise<InstalledApp[]>`: A promise that resolves to a list of installed applications.

**Throws:**
- `APIError`: If there's an error retrieving the installed applications.


```typescript
async startApp(startCmd: string, workDirectory: string = ""): Promise<Process[]>
```

**Parameters:**
- `startCmd` (string): The command used to start the application.
- `workDirectory` (string, optional): The working directory for the application. Default is an empty string.

**Returns:**
- `Promise<Process[]>`: A promise that resolves to a list of processes started.

**Throws:**
- `APIError`: If there's an error starting the application.


```typescript
async stopAppByPName(pname: string): Promise<boolean>
```

**Parameters:**
- `pname` (string): The name of the process to stop.

**Returns:**
- `Promise<boolean>`: A promise that resolves to true if the operation was successful, false otherwise.

**Throws:**
- `APIError`: If there's an error stopping the application.


```typescript
async stopAppByPid(pid: number): Promise<boolean>
```

**Parameters:**
- `pid` (number): The process ID to stop.

**Returns:**
- `Promise<boolean>`: A promise that resolves to true if the operation was successful, false otherwise.

**Throws:**
- `APIError`: If there's an error stopping the application.


```typescript
async stopAppByCmd(stopCmd: string): Promise<boolean>
```

**Parameters:**
- `stopCmd` (string): The command used to stop the application.

**Returns:**
- `Promise<boolean>`: A promise that resolves to true if the operation was successful, false otherwise.

**Throws:**
- `APIError`: If there's an error stopping the application.


```typescript
async listVisibleApps(): Promise<Process[]>
```

**Returns:**
- `Promise<Process[]>`: A promise that resolves to a list of visible processes.

**Throws:**
- `APIError`: If there's an error listing the visible applications.
