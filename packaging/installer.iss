#define MyAppVersion "0.3.0"
#ifndef Variant
#define Variant "Full"
#endif
#if Variant == "Lite"
#define SourceFolder "ApplyPilotLite"
#else
#define SourceFolder "ApplyPilot"
#endif
[Setup]
AppId={{9B7DF023-BF23-4660-9C48-19CD45B93374}
AppName=ApplyPilot
AppVersion={#MyAppVersion}
DefaultDirName={localappdata}\Programs\ApplyPilot
DefaultGroupName=ApplyPilot
PrivilegesRequired=lowest
OutputDir=..\installer-output
OutputBaseFilename=ApplyPilot-{#Variant}-Setup
Compression=lzma2/fast
SolidCompression=yes
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0.17763
UninstallDisplayIcon={app}\ApplyPilot.exe
WizardStyle=modern
[Files]
Source: "..\dist\{#SourceFolder}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
#if Variant == "Lite"
[InstallDelete]
Type: filesandordirs; Name: "{app}\_internal\browsers"
#endif
[Icons]
Name: "{group}\ApplyPilot"; Filename: "{app}\ApplyPilot.exe"
Name: "{autodesktop}\ApplyPilot"; Filename: "{app}\ApplyPilot.exe"
[Run]
Filename: "{app}\ApplyPilot.exe"; Description: "Launch ApplyPilot"; Flags: nowait postinstall skipifsilent
