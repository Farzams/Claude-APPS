; Inno Setup 6 script.  64-bit only; works on Windows 7 SP1 and later.
#define AppName "TeXora Simple"
#define AppVer "1.0.0"
[Setup]
AppId={{A7C3B1E2-5D44-4F0A-8E1B-2C9D6F3A7B55}
AppName={#AppName}
AppVersion={#AppVer}
AppPublisher=TeXora
DefaultDirName={autopf}\TeXoraSimple
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
OutputDir=dist
OutputBaseFilename=TeXora-Simple-Setup
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
