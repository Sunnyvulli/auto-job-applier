#define MyAppVersion "0.1.0"
[Setup]
AppId={{9B7DF023-BF23-4660-9C48-19CD45B93374}
AppName=ApplyPilot
AppVersion={#MyAppVersion}
DefaultDirName={localappdata}\Programs\ApplyPilot
DefaultGroupName=ApplyPilot
PrivilegesRequired=lowest
OutputDir=..\installer-output
OutputBaseFilename=ApplyPilot-Setup
Compression=lzma2/fast
SolidCompression=yes
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayIcon={app}\ApplyPilot.exe
[Files]
Source: "..\dist\ApplyPilot\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
[Icons]
Name: "{group}\ApplyPilot"; Filename: "{app}\ApplyPilot.exe"
Name: "{autodesktop}\ApplyPilot"; Filename: "{app}\ApplyPilot.exe"
[Run]
Filename: "{app}\ApplyPilot.exe"; Description: "Launch ApplyPilot"; Flags: nowait postinstall skipifsilent
