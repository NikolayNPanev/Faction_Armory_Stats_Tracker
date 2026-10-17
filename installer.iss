#define AppExe "dist\windows\FactionArmoryStatsTracker.exe"

[Setup]
AppId={{B3D49EA8-74D1-4821-8F6B-8D68D4958814}
AppName=Faction Armory Stats Tracker
AppVersion=0.1.0
AppPublisher=Faction Armory Stats Tracker
DefaultDirName={localappdata}\Programs\FactionArmoryStatsTracker
DefaultGroupName=Faction Armory Stats Tracker
PrivilegesRequired=lowest
UninstallDisplayIcon={app}\FactionArmoryStatsTracker.exe
OutputDir=dist\installer
OutputBaseFilename=FactionArmoryStatsTracker-Setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: unchecked

[Files]
Source: "{#AppExe}"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\Faction Armory Stats Tracker"; Filename: "{app}\FactionArmoryStatsTracker.exe"
Name: "{autodesktop}\Faction Armory Stats Tracker"; Filename: "{app}\FactionArmoryStatsTracker.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\FactionArmoryStatsTracker.exe"; Description: "Launch Faction Armory Stats Tracker"; Flags: postinstall nowait skipifsilent
