; Inno Setup script - builds PDFToolkit-Setup.exe from the PyInstaller one-folder build
[Setup]
AppName=PDF Toolkit
AppVersion=6.1
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
Source: "reader.ico"; DestDir: "{app}"; Flags: ignoreversion
Source: "math.ico"; DestDir: "{app}"; Flags: ignoreversion

; One program, three start-menu apps: the full toolkit, a Reader and Math Studio (own icons, own taskbar entries)
[Icons]
Name: "{group}\PDF Toolkit"; Filename: "{app}\PDFToolkit.exe"
Name: "{group}\PDF Toolkit Reader"; Filename: "{app}\PDFToolkit.exe"; Parameters: "--mode reader"; IconFilename: "{app}\reader.ico"
Name: "{group}\Math Studio"; Filename: "{app}\PDFToolkit.exe"; Parameters: "--mode math"; IconFilename: "{app}\math.ico"
Name: "{autodesktop}\PDF Toolkit"; Filename: "{app}\PDFToolkit.exe"; Tasks: desktopicon
Name: "{autodesktop}\PDF Toolkit Reader"; Filename: "{app}\PDFToolkit.exe"; Parameters: "--mode reader"; IconFilename: "{app}\reader.ico"; Tasks: desktopreader
Name: "{autodesktop}\Math Studio"; Filename: "{app}\PDFToolkit.exe"; Parameters: "--mode math"; IconFilename: "{app}\math.ico"; Tasks: desktopmath

[Tasks]
Name: "desktopicon"; Description: "Desktop shortcut: PDF Toolkit"; Flags: unchecked
Name: "desktopreader"; Description: "Desktop shortcut: PDF Toolkit Reader"; Flags: unchecked
Name: "desktopmath"; Description: "Desktop shortcut: Math Studio"; Flags: unchecked
Name: "openwith"; Description: "Add the Reader to the Open with list of book files (DjVu, EPUB, MOBI, FB2, CBZ, XPS)"; Flags: unchecked

; "Open with" only: nothing is taken over from the program you use now
[Registry]
Root: HKA; Subkey: "Software\Classes\PDFToolkit.Reader"; ValueType: string; ValueData: "PDF Toolkit Reader"; Flags: uninsdeletekey; Tasks: openwith
Root: HKA; Subkey: "Software\Classes\PDFToolkit.Reader\DefaultIcon"; ValueType: string; ValueData: "{app}\reader.ico"; Tasks: openwith
Root: HKA; Subkey: "Software\Classes\PDFToolkit.Reader\shell\open\command"; ValueType: string; ValueData: """{app}\PDFToolkit.exe"" --mode reader ""%1"""; Tasks: openwith
Root: HKA; Subkey: "Software\Classes\.djvu\OpenWithProgids"; ValueType: string; ValueName: "PDFToolkit.Reader"; ValueData: ""; Flags: uninsdeletevalue; Tasks: openwith
Root: HKA; Subkey: "Software\Classes\.djv\OpenWithProgids"; ValueType: string; ValueName: "PDFToolkit.Reader"; ValueData: ""; Flags: uninsdeletevalue; Tasks: openwith
Root: HKA; Subkey: "Software\Classes\.epub\OpenWithProgids"; ValueType: string; ValueName: "PDFToolkit.Reader"; ValueData: ""; Flags: uninsdeletevalue; Tasks: openwith
Root: HKA; Subkey: "Software\Classes\.mobi\OpenWithProgids"; ValueType: string; ValueName: "PDFToolkit.Reader"; ValueData: ""; Flags: uninsdeletevalue; Tasks: openwith
Root: HKA; Subkey: "Software\Classes\.fb2\OpenWithProgids"; ValueType: string; ValueName: "PDFToolkit.Reader"; ValueData: ""; Flags: uninsdeletevalue; Tasks: openwith
Root: HKA; Subkey: "Software\Classes\.cbz\OpenWithProgids"; ValueType: string; ValueName: "PDFToolkit.Reader"; ValueData: ""; Flags: uninsdeletevalue; Tasks: openwith
Root: HKA; Subkey: "Software\Classes\.xps\OpenWithProgids"; ValueType: string; ValueName: "PDFToolkit.Reader"; ValueData: ""; Flags: uninsdeletevalue; Tasks: openwith

[Run]
Filename: "{app}\PDFToolkit.exe"; Description: "Launch PDF Toolkit"; Flags: nowait postinstall skipifsilent
