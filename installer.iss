[Setup]
AppName=CodeZen India
AppVersion=1.0.0
AppPublisher=Shubh Mishra
AppPublisherURL=https://github.com/ShubhxD69
DefaultDirName={autopf}\CodeZen India
DefaultGroupName=CodeZen India
OutputDir=dist
OutputBaseFilename=CodeZenIndiaSetup
Compression=lzma
SolidCompression=yes
WizardStyle=modern
SetupIconFile=assets\icons\logo.ico
UninstallDisplayIcon={app}\CodeZen India.exe

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create Desktop Shortcut"; GroupDescription: "Additional Shortcuts:"; Flags: unchecked

[Files]
Source: "dist\CodeZen India.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "assets\icons\logo.ico"; DestDir: "{app}\assets\icons"; Flags: ignoreversion

[Icons]
Name: "{group}\CodeZen India"; Filename: "{app}\CodeZen India.exe"
Name: "{autodesktop}\CodeZen India"; Filename: "{app}\CodeZen India.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\CodeZen India.exe"; Description: "Launch CodeZen India"; Flags: nowait postinstall skipifsilent