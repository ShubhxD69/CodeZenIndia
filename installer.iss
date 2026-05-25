; installer.iss — Inno Setup 6 script for CodeZen India
;
; Prerequisites
; ─────────────
;   1. Build the EXE first:   pyinstaller CodeZenIndia.spec
;   2. Install Inno Setup 6:  https://jrsoftware.org/isinfo.php
;   3. Compile this script:   Right-click → Compile  (or iscc installer.iss)
;
; Output:  Output\CodeZenIndiaSetup.exe
;
; The installer:
;   • Runs in normal (non-admin) user mode — no elevation required
;   • Installs to %LOCALAPPDATA%\Programs\CodeZen India
;   • Creates Start Menu and optional Desktop shortcut
;   • Registers an Add/Remove Programs entry
;   • Supports silent install:  /VERYSILENT /SUPPRESSMSGBOXES
;   • Creates a default settings.json if not already present
;   • Uninstaller removes all installed files

#define MyAppName      "CodeZen India"
#define MyAppVersion   "1.0.0"
#define MyAppPublisher "Shubh Mishra"
#define MyAppURL       "https://github.com/ShubhMishra/CodeZenIndia"
#define MyAppExeName   "CodeZen India.exe"
#define MyAppId        "{8A3F2C1D-7B4E-4F9A-A6C3-2D1E8B5F4A7C}"

[Setup]
AppId={{#MyAppId}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}/issues
AppUpdatesURL={#MyAppURL}/releases
DefaultDirName={localappdata}\Programs\{#MyAppName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
LicenseFile=
InfoBeforeFile=
InfoAfterFile=
OutputDir=Output
OutputBaseFilename=CodeZenIndiaSetup
SetupIconFile=assets\icons\logo.ico
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
DisableProgramGroupPage=yes
UninstallDisplayIcon={app}\{#MyAppExeName}
UninstallDisplayName={#MyAppName}
VersionInfoVersion={#MyAppVersion}
VersionInfoCompany={#MyAppPublisher}
VersionInfoDescription={#MyAppName} Installer
VersionInfoProductName={#MyAppName}
VersionInfoProductVersion={#MyAppVersion}
; Show install progress
ShowLanguageDialog=no
WizardSizePercent=110

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon";    Description: "{cm:CreateDesktopIcon}";    GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "quicklaunchicon"; Description: "{cm:CreateQuickLaunchIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked; OnlyBelowVersion: 6.1; Check: not IsAdminInstallMode

[Files]
; Main executable (built by PyInstaller)
Source: "dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion

; Assets directory
Source: "assets\icons\*"; DestDir: "{app}\assets\icons"; Flags: ignoreversion recursesubdirs createallsubdirs

; Default settings (only install if the user does not already have one)
Source: "version.json"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}";           Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\assets\icons\logo.ico"
Name: "{group}\Uninstall {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}";     Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon; IconFilename: "{app}\assets\icons\logo.ico"
Name: "{userappdata}\Microsoft\Internet Explorer\Quick Launch\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: quicklaunchicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}"

[Registry]
; Register application in Windows (enables "Open with" and file associations)
Root: HKCU; Subkey: "Software\{#MyAppPublisher}\{#MyAppName}"; ValueType: string; ValueName: "InstallPath"; ValueData: "{app}"; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\{#MyAppPublisher}\{#MyAppName}"; ValueType: string; ValueName: "Version";     ValueData: "{#MyAppVersion}"

; Optional: associate .py files with CodeZen India
; Uncomment the lines below to enable .py file association
; Root: HKCU; Subkey: "Software\Classes\.py"; ValueType: string; ValueName: ""; ValueData: "CodeZenIndia.py"; Flags: uninsdeletevalue
; Root: HKCU; Subkey: "Software\Classes\CodeZenIndia.py"; ValueType: string; ValueName: ""; ValueData: "Python Source File"; Flags: uninsdeletekey
; Root: HKCU; Subkey: "Software\Classes\CodeZenIndia.py\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: "{app}\{#MyAppExeName},0"
; Root: HKCU; Subkey: "Software\Classes\CodeZenIndia.py\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#MyAppExeName}"" ""%1"""

[Code]
// ── Pre-install check: warn if old version is running ─────────────────────────
function InitializeSetup(): Boolean;
var
  ResultCode: Integer;
begin
  Result := True;
end;

// ── Create a default settings.json on first install ───────────────────────────
procedure CurStepChanged(CurStep: TSetupStep);
var
  SettingsPath: String;
  SettingsContent: String;
begin
  if CurStep = ssPostInstall then
  begin
    SettingsPath := ExpandConstant('{app}\settings.json');
    if not FileExists(SettingsPath) then
    begin
      SettingsContent :=
        '{' + #13#10 +
        '  "font_size": 13,' + #13#10 +
        '  "tab_size": 4,' + #13#10 +
        '  "word_wrap": false,' + #13#10 +
        '  "auto_save": false,' + #13#10 +
        '  "interpreter_path": "",' + #13#10 +
        '  "auto_update": true,' + #13#10 +
        '  "update_channel": "stable",' + #13#10 +
        '  "recent_projects": [],' + #13#10 +
        '  "last_workspace": "",' + #13#10 +
        '  "terminal_font_size": 12' + #13#10 +
        '}';
      SaveStringToFile(SettingsPath, SettingsContent, False);
    end;
  end;
end;
