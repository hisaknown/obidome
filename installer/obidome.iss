; Inno Setup script for Obidome.
; Build with: iscc /DAppVersion=x.y.z installer/obidome.iss

#ifndef AppVersion
  #define AppVersion "0.0.0"
#endif

[Setup]
AppId={{6F2B8C1E-4A7D-4E3B-9C5A-0B1D2E3F4A5B}
AppName=Obidome
AppVersion={#AppVersion}
AppPublisher=Hisano Kujirai
DefaultDirName={localappdata}\Programs\Obidome
DefaultGroupName=Obidome
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir=..\.nuitka
OutputBaseFilename=ObidomeSetup-{#AppVersion}
SetupIconFile=..\src\obidome\res\icon.ico
UninstallDisplayIcon={app}\obidome.exe
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
CloseApplications=yes

[Languages]
Name: "japanese"; MessagesFile: "compiler:Languages\Japanese.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "startup"; Description: "Windows の起動時に Obidome を開始する"; GroupDescription: "その他:"

[Files]
Source: "..\.nuitka\main.dist\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Obidome"; Filename: "{app}\obidome.exe"
Name: "{group}\Obidome のアンインストール"; Filename: "{uninstallexe}"
Name: "{userstartup}\Obidome"; Filename: "{app}\obidome.exe"; Tasks: startup

[Run]
Filename: "{app}\obidome.exe"; Description: "Obidome を起動する"; Flags: nowait postinstall skipifsilent

[UninstallRun]
Filename: "taskkill"; Parameters: "/IM obidome.exe /F"; Flags: runhidden; RunOnceId: "KillObidome"
