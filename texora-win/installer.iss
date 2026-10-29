; Inno Setup 6 script.  64-bit only; works on Windows 7 SP1 and later.
#define AppName "TeXora"
#define AppVer "1.0.0"
[Setup]
AppId={{6D1F7C52-3B7B-4C8B-9D58-7E2B0C9E4A11}
AppName={#AppName}
AppVersion={#AppVer}
AppPublisher=TeXora
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
OutputDir=dist
OutputBaseFilename=TeXora-Setup
SetupIconFile=icon.ico
UninstallDisplayIcon={app}\TeXora.exe
Compression=lzma2/normal
SolidCompression=yes
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64
MinVersion=6.1sp1
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
WizardStyle=modern
[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; Flags: unchecked
[Files]
Source: "dist\TeXora\*"; DestDir: "{app}"; Flags: recursesubdirs ignoreversion
[Icons]
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\TeXora.exe"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\TeXora.exe"; Tasks: desktopicon
[Run]
Filename: "{app}\TeXora.exe"; Description: "Start TeXora"; Flags: nowait postinstall skipifsilent
