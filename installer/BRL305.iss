; BRL-305 Monitor - minimal installer (Inno Setup 6)
; Wraps the PyInstaller one-file exe: Program Files + Start Menu/Desktop shortcuts + uninstaller,
; and installs the VC++ 2015-2022 x86 runtime (UCRT) that a bare Windows 7 x86 box needs.

#define AppName "BRL-305 Monitor"
#define AppVer "1.0.0"
#define AppExe "BRL305_Monitor.exe"
#ifndef SrcDir
  #define SrcDir "."
#endif

[Setup]
AppId={{8F2A9C11-4B7E-4E2A-9C3D-BRL305MONITOR}}
AppName={#AppName}
AppVersion={#AppVer}
AppPublisher=Accurate Systems
DefaultDirName={autopf}\BRL305 Monitor
DefaultGroupName=BRL-305 Monitor
DisableProgramGroupPage=yes
OutputDir=Output
OutputBaseFilename=BRL305_Setup
Compression=lzma2
SolidCompression=yes
; empty => install as 32-bit so {autopf} resolves to Program Files (x86) on 64-bit Windows
ArchitecturesInstallIn64BitMode=
WizardStyle=modern
UninstallDisplayIcon={app}\{#AppExe}

[Files]
Source: "{#SrcDir}\{#AppExe}"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#SrcDir}\vc_redist.x86.exe"; DestDir: "{tmp}"; Flags: deleteafterinstall

[Icons]
Name: "{group}\BRL-305 Monitor"; Filename: "{app}\{#AppExe}"
Name: "{commondesktop}\BRL-305 Monitor"; Filename: "{app}\{#AppExe}"

[Run]
; vc_redist self-skips if already present; /quiet keeps it invisible. Needed for the tunnel's
; ssl/sqlite3/certifi on a bare Win7 x86 box (the app's startup preflight names it if still missing).
Filename: "{tmp}\vc_redist.x86.exe"; Parameters: "/quiet /norestart"; StatusMsg: "Installing runtime components..."; Flags: waituntilterminated
Filename: "{app}\{#AppExe}"; Description: "Launch BRL-305 Monitor"; Flags: nowait postinstall skipifsilent
