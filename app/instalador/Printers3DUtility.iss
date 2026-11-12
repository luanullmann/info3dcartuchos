; Instalador do Printer's 3D Utility (Inno Setup 6)
; Compilar:  iscc instalador\Printers3DUtility.iss   (depois de gerar dist\Printers3DUtility.exe)

#ifndef AppVersion
  #define AppVersion "2.0"
#endif

[Setup]
AppId={{333A9EAD-A9AE-471B-ACE0-F5898EFF7DC0}
AppName=Printer's 3D Utility
AppVersion={#AppVersion}
AppVerName=Printer's 3D Utility {#AppVersion}
AppPublisher=Info 3D Cartuchos Express
AppPublisherURL=https://luanullmann.github.io/info3dcartuchos/
AppSupportURL=https://wa.me/5521986600466
DefaultDirName={localappdata}\Programs\Printers3DUtility
DefaultGroupName=Printer's 3D Utility
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir=..\dist
OutputBaseFilename=Printers3DUtility-Setup
SetupIconFile=..\src\img\icone.ico
UninstallDisplayIcon={app}\Printers3DUtility.exe
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
LicenseFile=..\LICENCA_epson_print_conf.txt

[Languages]
Name: "ptbr"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"

[Tasks]
Name: "desktopicon"; Description: "Criar atalho na Área de Trabalho"; GroupDescription: "Atalhos:"

[Files]
Source: "..\dist\Printers3DUtility.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\Printer's 3D Utility"; Filename: "{app}\Printers3DUtility.exe"
Name: "{group}\Pasta de dados (backups e fotos)"; Filename: "{userdocs}\Printer's 3D Utility"
Name: "{group}\Desinstalar Printer's 3D Utility"; Filename: "{uninstallexe}"
Name: "{userdesktop}\Printer's 3D Utility"; Filename: "{app}\Printers3DUtility.exe"; Tasks: desktopicon

[Dirs]
Name: "{userdocs}\Printer's 3D Utility"; Flags: uninsneveruninstall

[Run]
Filename: "{app}\Printers3DUtility.exe"; Description: "Abrir o Printer's 3D Utility agora"; Flags: nowait postinstall skipifsilent

[Messages]
ptbr.WelcomeLabel2=Este assistente vai instalar o [name/ver] no seu computador.%n%nReset de almofadas Epson por Wi-Fi e USB, diagnóstico, tabela de erros e teste de impressão.%n%nInfo 3D Cartuchos Express • WhatsApp (21) 98660-0466
