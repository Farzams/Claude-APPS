; Inno Setup script - builds PDFToolkit-Setup.exe from the PyInstaller one-folder build
[Setup]
AppName=PDF Toolkit
AppVersion=2.0
AppPublisher=PDF Toolkit
DefaultDirName={autopf}\PDF Toolkit
DefaultGroupName=PDF Toolkit
OutputDir=dist
OutputBaseFilename=PDFToolkit-Setup
SetupIconFile=icon.ico
UninstallDisplayIcon={app}\PDFToolkit.exe
Compression=lzma2/fast
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
ArchitecturesInstallIn64BitMode=x64compatible

[Files]
Source: "dist\PDFToolkit\*"; DestDir: "{app}"; Flags: recursesubdirs ignoreversion

[Icons]
Name: "{group}\PDF Toolkit"; Filename: "{app}\PDFToolkit.exe"
Name: "{autodesktop}\PDF Toolkit"; Filename: "{app}\PDFToolkit.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; Flags: unchecked

[Run]
Filename: "{app}\PDFToolkit.exe"; Description: "Launch PDF Toolkit"; Flags: nowait postinstall skipifsilent
