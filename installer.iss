; =========================================================
; CodeZen India Installer Script
; Inno Setup Script
; =========================================================

#define MyAppName "CodeZen India"
#define MyAppVersion "1.1.0"
#define MyAppPublisher "Shubh Mishra"
#define MyAppExeName "CodeZen India.exe"

[Setup]
AppId={{C0DEZEN-INDIA-IDE}}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\CodeZen India
DefaultGroupName=CodeZen India
AllowNoIcons=yes
LicenseFile=LICENSE
OutputDir=Output
OutputBaseFilename=CodeZenIndiaSetup
Compression=lzma
SolidCompression=yes
WizardStyle=modern
SetupIconFile=assets\icons\logo.ico
UninstallDisplayIcon={app}{#MyAppExeName}

PrivilegesRequired=admin

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]

; Desktop shortcut already selected
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional icons:"; Flags: checkedonce

[Files]

; Main EXE
Source: "dist\CodeZen India.exe"; DestDir: "{app}"; Flags: ignoreversion

; Additional files
Source: "README.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "LICENSE"; DestDir: "{app}"; Flags: ignoreversion
Source: "version.json"; DestDir: "{app}"; Flags: ignoreversion

[Icons]

; Start Menu Shortcut
Name: "{group}\CodeZen India"; Filename: "{app}{#MyAppExeName}"

; Desktop Shortcut
Name: "{autodesktop}\CodeZen India"; Filename: "{app}{#MyAppExeName}"; Tasks: desktopicon

[Run]

; Launch app after installation
Filename: "{app}{#MyAppExeName}"; Description: "Launch CodeZen India"; Flags: nowait postinstall skipifsilent

[Code]

function InitializeSetup(): Boolean;
begin
Result := True;
end;
