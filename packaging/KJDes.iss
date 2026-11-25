; ─────────────────────────────────────────────────────────────────────────
;  KJ Des — Inno Setup installer (includes inherited installer logic; see NOTICE.md)
;  Derleme: once scripts\Build.bat (PyInstaller -> dist\KJ Des\KJDes.exe),
;           sonra bu dosyayi Inno Setup ile derle (ISCC packaging\KJ Des.iss).
;  Cikti:   installer\KJ Des-Setup-<surum>.exe
; ─────────────────────────────────────────────────────────────────────────

#define MyAppName "KJ Des"
#define MyAppVersion "1.0.4"
#define MyAppPublisher "Lucas"
#define MyAppURL "https://github.com/LUCASS7001"
#define MyAppExeName "KJDes.exe"
#define MyAppGuid "{B3E5C2A8-6F41-4D7A-9C1E-5A8D2F7B4E19}"
#define MyAppId "{" + MyAppGuid
#ifndef MyDistDir
  #define MyDistDir "..\dist\KJDes"
#endif

[Setup]
AppId={#MyAppId}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
VersionInfoVersion={#MyAppVersion}
VersionInfoCompany={#MyAppPublisher}
VersionInfoDescription=KJ Des Setup
VersionInfoProductName={#MyAppName}
VersionInfoCopyright=Copyright (c) 2026 {#MyAppPublisher}. Includes third-party components; see NOTICE.md.
AppCopyright=Copyright (c) 2026 {#MyAppPublisher}. Includes third-party components; see NOTICE.md.
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppComments=A Windows desktop connectivity utility for Discord.

; KURULUM DIZINI POLITIKASI (guvenlik)
; ONLOGON + HIGHEST failsafe gorevinin hedefi, kullanici tarafindan
; DEGISTIRILEMEYEN bir konumda olmak ZORUNDADIR. Bu yuzden:
;   - DisableDirPage=yes : kullanici sihirbazda baska bir dizin secemez.
;   - UsePreviousAppDir=no: onceki (belki custom, belki gevsek ACL'li) kurulum
;     dizini SESSIZCE devralinmaz; her zaman {autopf}\KJ Des kullanilir.
; `/DIR=` komut satiri hala geciriebilir; bu yuzden hedef, gorev kurulmadan
; once [Code] icinde BAGIMSIZ olarak dogrulanir (PathIsVerifiedInstall) ve
; dogrulanamazsa kurulum gorunur bicimde basarisiz olur.
DefaultDirName={autopf}\{#MyAppName}
DisableDirPage=yes
UsePreviousAppDir=no
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
UninstallDisplayIcon={app}\{#MyAppExeName}
UninstallDisplayName={#MyAppName} {#MyAppVersion}

; Kurulum yonetici ister (KJ Des zaten yonetici haklariyla calisir)
PrivilegesRequired=admin
ArchitecturesInstallIn64BitMode=x64compatible

; Restart Manager `force` kipinde bile once 30 saniye nazik kapanis bekler.
; KJ Des pasifse [Code]/PrepareToInstall, TAM kurulu exe yolunu dogrulayip yalniz
; o sureci hemen kapatir. Aktif/bilinmeyen ag durumunda kurulum fail-closed
; durur. Restart Manager'i kapatmak bu gereksiz 30 saniyeyi tamamen kaldirir.
CloseApplications=no
RestartApplications=no

; Cikti
OutputDir=..\installer
OutputBaseFilename=KJDes-Setup-{#MyAppVersion}
SetupIconFile=..\app\assets\icon.ico
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
WizardSmallImageFile=assets\wizard-small-55.bmp,assets\wizard-small-110.bmp
DisableWelcomePage=no

[Languages]
Name: "arabic"; MessagesFile: "compiler:Languages\Arabic.isl"
Name: "turkish"; MessagesFile: "compiler:Languages\Turkish.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[CustomMessages]
arabic.ActiveConnectionBlock=يرجى فصل الاتصال في KJ Des واستعادة الإعدادات الافتراضية قبل التحديث. أُلغي التثبيت.
turkish.ActiveConnectionBlock=Güncelleme için önce KJ Des'te Varsayılana Dönün. Kurulum iptal edildi.
english.ActiveConnectionBlock=Restore Defaults in KJ Des before updating. Setup was cancelled.
arabic.PendingRestoreRunning=KJ Des يعمل ولم يُكمل بعد استعادة إعدادات DNS الأصلية. أغلق KJ Des من قائمة شريط المهام (خروج) ثم شغّل التثبيت مجددًا. نسختك الاحتياطية من DNS محفوظة ولم يُغيَّر شيء.
turkish.PendingRestoreRunning=KJ Des çalışıyor ve orijinal DNS ayarlarınızı henüz geri yüklemedi. KJ Des'i tepsi menüsünden (Çıkış) kapatıp kurulumu yeniden çalıştırın. DNS yedeğiniz korunuyor; hiçbir şey değiştirilmedi.
english.PendingRestoreRunning=KJ Des is running and has not finished restoring your original DNS settings. Quit KJ Des from the tray menu (Exit), then run Setup again. Your DNS backup is kept and nothing was changed.
arabic.PassiveCloseFailed=تعذّر إغلاق KJ Des بأمان. أُلغي التثبيت؛ أغلق KJ Des وحاول مجددًا.
turkish.PassiveCloseFailed=KJ Des güvenli biçimde kapatılamadı. Kurulum iptal edildi; KJ Des'i kapatıp yeniden deneyin.
english.PassiveCloseFailed=KJ Des could not be closed safely. Setup was cancelled; close KJ Des and try again.
arabic.UninstallNeedsRestore=لم يُكمل KJ Des استعادة إعدادات الشبكة بعد:%n%n%1%nافتح KJ Des، فهو يستعيدها تلقائيًا عند التشغيل. إن بقي تحذير، استخدم الإعدادات ← استعادة الإعدادات الافتراضية، ثم شغّل أداة الإزالة مجددًا.%n%nلم تتم إزالة أي شيء.
turkish.UninstallNeedsRestore=KJ Des ağ ayarlarını henüz geri yüklemedi:%n%n%1%nKJ Des'i açın; açılışta bunları otomatik olarak geri yükler. Uyarı kalırsa Ayarlar → Varsayılana dön'ü kullanın, ardından kaldırıcıyı yeniden çalıştırın.%n%nHiçbir şey kaldırılmadı.
english.UninstallNeedsRestore=KJ Des has not finished restoring your network settings:%n%n%1%nOpen KJ Des — it restores them automatically when it starts. If a warning remains, use Settings → Restore defaults, then run the uninstaller again.%n%nNothing was removed.
arabic.ResidueHosts=• توجيه Discord الخاص بـ KJ Des ما زال في ملف hosts
turkish.ResidueHosts=• KJ Des'in Discord yönlendirmesi hâlâ hosts dosyasında
english.ResidueHosts=• KJ Des's Discord routing is still in the hosts file
arabic.ResidueDns=• إعدادات DNS الأصلية لم تُستعد بعد
turkish.ResidueDns=• Orijinal DNS ayarlarınız henüz geri yüklenmedi
english.ResidueDns=• Your original DNS settings have not been restored yet
arabic.UninstallCloseFailed=تعذّر إغلاق KJ Des بأمان. أُلغيت الإزالة؛ أغلق KJ Des من قائمة شريط المهام (خروج) وحاول مجددًا.
turkish.UninstallCloseFailed=KJ Des güvenli biçimde kapatılamadı. Kaldırma iptal edildi; KJ Des'i tepsi menüsünden (Çıkış) kapatıp yeniden deneyin.
english.UninstallCloseFailed=KJ Des could not be closed safely. Uninstall was cancelled; quit KJ Des from the tray menu (Exit) and try again.
arabic.UninstallUiFailed=تعذّر فتح شاشة الإزالة. لم يُحذف أي ملف.
turkish.UninstallUiFailed=Kaldırma ekranı açılamadı. Hiçbir dosya silinmedi.
english.UninstallUiFailed=The uninstall window could not be opened. No files were removed.
arabic.UninstallHostsFailed=تتم إزالة KJ Des، لكن تعذّر حذف توجيه Discord الخاص به من ملف hosts.%n%nلن يعمل Discord ما دامت هذه الأسطر موجودة. احذف الكتلة «KJ Des Discord connectivity» يدويًا من الملف:%n%%WinDir%%\System32\drivers\etc\hosts
turkish.UninstallHostsFailed=KJ Des kaldırılıyor, ancak hosts dosyasındaki Discord yönlendirmesi temizlenemedi.%n%nBu satırlar kalırsa Discord açılmaz. Lütfen "KJ Des Discord connectivity" bloğunu elle silin:%n%%WinDir%%\System32\drivers\etc\hosts
english.UninstallHostsFailed=KJ Des is being removed, but its Discord routing could not be removed from the hosts file.%n%nDiscord will not open while these lines remain. Please delete the "KJ Des Discord connectivity" block manually from:%n%%WinDir%%\System32\drivers\etc\hosts
arabic.UserDataPartial=تمت إزالة KJ Des، لكن تعذّر حذف بعض ملفات الإعدادات/السجل:
turkish.UserDataPartial=KJ Des kaldırıldı, ancak ayar/günlük dosyalarının tamamı silinemedi:
english.UserDataPartial=KJ Des was removed, but some settings/log files could not be deleted:

[Tasks]
; Bayrak yok = kutu VARSAYILAN OLARAK ISARETLI gelir (masaustu kisayolu olusur).
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "{#MyDistDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
; Ikonu ayrica kurulum kokune acikca kopyala (assets alt klasorunden bagimsiz,
; kararli bir yol); kisayollar bu dosyayi acikca referans alir.
Source: "..\app\assets\icon.ico"; DestDir: "{app}"; DestName: "icon.ico"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\icon.ico"; IconIndex: 0
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"; Parameters: "/SILENT /KJDESUI=1 /NORESTART"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon; IconFilename: "{app}\icon.ico"; IconIndex: 0

[Run]
; Kurulum bitince istege bagli baslat. KJDes.exe yonetici (requireAdministrator)
; ister; runascurrentuser ile CreateProcess "kod 740" verir. shellexec, ShellExecute
; kullanip manifesti onurlandirir ve dogru sekilde yukseltir.
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#MyAppName}}"; Flags: nowait postinstall skipifsilent shellexec

; Not: Kaldirma temizligi (hosts blogunu sil + failsafe gorevini sil + calisan
; KJ Des'i kapat) [Code] icinde CurUninstallStepChanged'te yapilir. Eski [UninstallRun]
; yaklasimi ({sys} + admin-exe --cleanup-hosts) kaldiricida "PathRedir: Not
; initialized" ic hatasi veriyordu. Ayarlar/loglar yalniz acik kullanici secimiyle silinir.

[Code]
const
  SHCNE_ASSOCCHANGED = $08000000;
  SHCNF_IDLIST       = $0000;
  { TASK_NAME / LEGACY_TASK, testlerin ayikladigi karar blogunun icinde
    tanimlidir (bkz. KJDES FAILSAFE TASK BEGIN): blok kendi kendine yeterli
    olmalidir. }

procedure SHChangeNotify(wEventId: LongWord; uFlags: LongWord; dwItem1: LongWord; dwItem2: LongWord);
  external 'SHChangeNotify@shell32.dll stdcall';

function InitializeSetup(): Boolean;
begin
  Result := True;
end;

{ DIKKAT: Asagidaki isaretli blok tests/test_failsafe_reconcile.py tarafindan
  AYIKLANIP ayri bir deneme kurulumuna derlenir ve GECICI fixture dosyalari
  uzerinde CALISTIRILIR. Blok kendi kendine yeterli olmalidir (disaridaki
  sabitlere/rutinlere bagli degil) ve isaret satirlari AYNEN korunmalidir. }
{ ===== KJDES HOSTS CLEANER BEGIN ===== }
const
  HOSTS_BEGIN  = '# >>> KJ Des Discord connectivity >>>';
  HOSTS_END    = '# <<< KJ Des Discord connectivity <<<';
  LEGACY_BEGIN = '# >>> KJ Des Discord connectivity >>>';  { no foreign markers }
  LEGACY_END   = '# <<< KJ Des Discord connectivity <<<';

function SetFileAttributesW(lpFileName: string; dwAttrs: LongWord): Boolean;
  external 'SetFileAttributesW@kernel32.dll stdcall';

{ Satir, KJ Des'in YAZDIGI yonlendirmelerden biri mi? Yalniz tam olarak
  '127.0.0.1 <bilinen discord host>' bicimindeki satirlar bize aittir;
  app/core/discord_unblock.py::BLOCKED_HOSTS ile ayni kume. }
function HostsLineIsOurRedirect(const Line: string): Boolean;
var
  S, Host: string;
begin
  Result := False;
  S := Trim(Line);
  if Copy(S, 1, 9) <> '127.0.0.1' then exit;
  { 10. karakter bir ayirici olmali: '127.0.0.10 x' veya '127.0.0.1x' bize ait
    degildir. Trim sonrasi tek bir alan kalmalidir. }
  S := Trim(Copy(S, 10, Length(S)));
  if S = '' then exit;
  if Pos(' ', S) > 0 then exit;
  if Pos(#9, S) > 0 then exit;
  Host := Lowercase(S);
  Result := (Host = 'updates.discord.com') or (Host = 'discord.com')
         or (Host = 'gateway.discord.gg') or (Host = 'cdn.discordapp.com')
         or (Host = 'media.discordapp.net');
end;

{ KJ Des residue = a KJ Des marker line. The app always writes its redirects
  inside its own marked block, so bare '127.0.0.1 discord.com' lines OUTSIDE
  that block belong to the user or another product (e.g. DPort) and must
  neither block uninstall nor be removed. (DPort 3.20 counts such bare lines
  as its own, which is why an active KJ Des block blocks DPort's uninstall.) }
function HostsHasKJDesResidue(const Lines: TArrayOfString): Boolean;
var
  I: Integer;
  S: string;
begin
  Result := True;
  for I := 0 to GetArrayLength(Lines) - 1 do begin
    S := Trim(Lines[I]);
    if (S = HOSTS_BEGIN) or (S = HOSTS_END)
       or (S = LEGACY_BEGIN) or (S = LEGACY_END) then exit;
  end;
  Result := False;
end;

function CleanHostsBlockUnsafe(const HostsPath: string): Boolean;
var
  Lines, OutLines, Verify: TArrayOfString;
  I, N: Integer;
  S: string;
  Skip: Boolean;
begin
  Result := False;

  { Dosya yok -> temizlenecek yonlendirme de yok: DOGRULANMIS temiz durum. }
  if not FileExists(HostsPath) then begin
    Result := True;
    exit;
  end;
  if not LoadStringsFromFile(HostsPath, Lines) then begin
    Log('KJ Des: hosts OKUNAMADI: ' + HostsPath);
    exit;
  end;
  { Isaretli blok ya da yonlendirme yok -> yazma YAPMA (kullanici dosyasini
    gereksiz yere yeniden yazmayiz), ama durum dogrulanmis temizdir. }
  if not HostsHasKJDesResidue(Lines) then begin
    Result := True;
    exit;
  end;

  SetArrayLength(OutLines, GetArrayLength(Lines));
  N := 0;
  Skip := False;
  for I := 0 to GetArrayLength(Lines) - 1 do begin
    S := Trim(Lines[I]);
    if (S = HOSTS_BEGIN) or (S = LEGACY_BEGIN) then begin Skip := True; continue; end;
    if (S = HOSTS_END) or (S = LEGACY_END) then begin Skip := False; continue; end;
    if Skip then begin
      { VERI KAYBI KORUMASI: bitis isareti eksikse (yarim yazma, elle mudahale)
        dosyanin GERI KALANI silinmemeli. Skip modunda YALNIZCA kendi bildigimiz
        yonlendirme satirlarini sileriz; yabanci bir satir gelince blogu bitmis
        sayar ve o satiri KORURUZ. (Ayni ilke:
        app/core/discord_unblock.py::_strip_block) }
      if HostsLineIsOurRedirect(S) then continue;
      Skip := False;
    end;
    OutLines[N] := Lines[I];
    N := N + 1;
  end;
  SetArrayLength(OutLines, N);

  if not SetFileAttributesW(HostsPath, FILE_ATTRIBUTE_NORMAL) then begin
    Log('KJ Des: hosts dosya nitelikleri degistirilemedi: ' + HostsPath);
    exit;
  end;
  if not SaveStringsToFile(HostsPath, OutLines, False) then begin
    Log('KJ Des: hosts YAZILAMADI: ' + HostsPath);
    exit;
  end;

  { Sonucu DISKTEN yeniden okuyup dogrula: isaretci veya yonlendirme kalmissa
    temizlik BASARISIZ sayilir (gorev bu yuzden korunur). }
  if not LoadStringsFromFile(HostsPath, Verify) then begin
    Log('KJ Des: hosts yazildi ama GERI OKUNAMADI: ' + HostsPath);
    exit;
  end;
  if HostsHasKJDesResidue(Verify) then begin
    Log('KJ Des: hosts temizligi DOGRULANAMADI (kalinti var): ' + HostsPath);
    exit;
  end;
  Result := True;
end;

{ hosts dosyasindan yalnizca KJ Des isaretli blogunu siler; KJ Des blogu, reklam
  engelleyici gibi diger tum satirlar korunur. Salt-okunur ise once acar.
  Donus: temizlik DISKTEN DOGRULANDI mi. False ise cagiran failsafe gorevini
  SILMEMELIDIR. }
function CleanHostsBlock(const HostsPath: string): Boolean;
begin
  try
    Result := CleanHostsBlockUnsafe(HostsPath);
  except
    Log('KJ Des: hosts temizliginde beklenmeyen hata: ' + GetExceptionMessage);
    Result := False;
  end;
end;
{ ===== KJDES HOSTS CLEANER END ===== }

function HostsFilePath(): string;
begin
  Result := ExpandConstant('{win}\System32\drivers\etc\hosts');
end;

{ ── Hedef dogrulama ILKELLERI ─────────────────────────────────────────────
  Asagidaki isaretli KARAR blogu yalnizca bu dort rutini kullanir. Testler ayni
  karar blogunu ayiklayip SAHTE ilkellerle derleyip calistirir. }

function GetFullPathNameW(lpFileName: string; nBufferLength: LongWord;
  lpBuffer: string; lpFilePart: LongWord): LongWord;
  external 'GetFullPathNameW@kernel32.dll stdcall';

function GetLongPathNameW(lpszShortPath: string; lpszLongPath: string;
  cchBuffer: LongWord): LongWord;
  external 'GetLongPathNameW@kernel32.dll stdcall';

function GetFileAttributesW(lpFileName: string): LongWord;
  external 'GetFileAttributesW@kernel32.dll stdcall';

{ Yolu GERCEK, tam nitelikli ve UZUN adli haline cevirir.
  - Goreli yol / '..' cozulur (GetFullPathName)
  - 8.3 kisa ad acilir (GetLongPathName); bu ayni zamanda yolun GERCEKTEN
    VAR OLDUGUNU da dogrular (yoksa cagri basarisiz olur)
  - Ag (UNC) yolu korumali kurulum sayilmaz -> reddedilir
  Junction/symlink burada COZULMEZ; zincir ayrica reparse point yonunden
  denetlenir ve varsa yol tamamen REDDEDILIR. }
function PathCanonical(const Path: string; var Canon: string): Boolean;
var
  Buf: string;
  Len: LongWord;
begin
  Result := False;
  Canon := '';
  if Trim(Path) = '' then exit;
  if Copy(Path, 1, 2) = '\\' then exit;
  SetLength(Buf, 4096);
  Len := GetFullPathNameW(Path, 4096, Buf, 0);
  if (Len = 0) or (Len >= 4096) then exit;
  SetLength(Buf, Integer(Len));
  Canon := Buf;
  SetLength(Buf, 4096);
  Len := GetLongPathNameW(Canon, Buf, 4096);
  if (Len = 0) or (Len >= 4096) then exit;
  SetLength(Buf, Integer(Len));
  Canon := Buf;
  if Copy(Canon, 1, 2) = '\\' then begin Canon := ''; exit; end;
  Result := True;
end;

{ Donus False = durum OKUNAMADI (cagiran FAIL CLOSED davranir). }
function PathIsReparse(const Path: string; var IsReparse: Boolean): Boolean;
var
  Attrs: LongWord;
begin
  IsReparse := False;
  Attrs := GetFileAttributesW(Path);
  if Attrs = $FFFFFFFF then begin
    Result := False;
    exit;
  end;
  IsReparse := (Attrs and $00000400) <> 0;   { FILE_ATTRIBUTE_REPARSE_POINT }
  Result := True;
end;

procedure AddRoot(var Roots: TArrayOfString; const Value: string);
var
  I, N: Integer;
  Clean: string;
begin
  Clean := Trim(Value);
  if Clean = '' then exit;
  while (Length(Clean) > 3) and (Clean[Length(Clean)] = '\') do
    Clean := Copy(Clean, 1, Length(Clean) - 1);
  for I := 0 to GetArrayLength(Roots) - 1 do
    if CompareText(Roots[I], Clean) = 0 then exit;
  N := GetArrayLength(Roots);
  SetArrayLength(Roots, N + 1);
  Roots[N] := Clean;
end;

{ GERCEK Program Files kokleri. ORTAM DEGISKENI KULLANILMAZ: kullanici
  HKCU\Environment uzerinden ProgramFiles/ProgramW6432 degerlerini
  degistirebildigi icin bunlar guvenilmez. Iki bagimsiz, YALNIZ YONETICININ
  yazabildigi kaynak kullanilir:
    1. Inno'nun kabuk API'sinden turettigi commonpf32 / commonpf64 sabitleri
    2. HKLM\...\CurrentVersion altindaki ProgramFilesDir degerleri }
function ProgramFilesRoots(var Roots: TArrayOfString): Boolean;
var
  S: string;
begin
  SetArrayLength(Roots, 0);
  try
    AddRoot(Roots, ExpandConstant('{commonpf32}'));
  except
  end;
  try
    AddRoot(Roots, ExpandConstant('{commonpf64}'));
  except
  end;
  if RegQueryStringValue(HKEY_LOCAL_MACHINE,
       'SOFTWARE\Microsoft\Windows\CurrentVersion', 'ProgramFilesDir', S) then
    AddRoot(Roots, S);
  if RegQueryStringValue(HKEY_LOCAL_MACHINE,
       'SOFTWARE\Microsoft\Windows\CurrentVersion', 'ProgramFilesDir (x86)', S) then
    AddRoot(Roots, S);
  if RegQueryStringValue(HKEY_LOCAL_MACHINE,
       'SOFTWARE\Microsoft\Windows\CurrentVersion', 'ProgramW6432Dir', S) then
    AddRoot(Roots, S);
  Result := GetArrayLength(Roots) > 0;
end;

function CapturedLinesText(const Lines: TArrayOfString): string;
var
  I: Integer;
begin
  Result := '';
  for I := 0 to GetArrayLength(Lines) - 1 do begin
    if Result <> '' then Result := Result + #13#10;
    Result := Result + Lines[I];
  end;
end;

{ Nesnenin guvenlik tanimlayicisini SDDL metni olarak dondurur (sahip + DACL).
  DACL'i isaretci aritmetigiyle gezmek yerine metin olarak almak, Pascal Script
  icinde deterministik ve denetlenebilir bir cozumleme saglar.
  powershell.exe MUTLAK yoldan (System32) calistirilir; PATH'e guvenilmez.

  GUVENLIK: Sonuc kullanici-yazilabilir TEMP dosyasina konmaz. Ayricalikli
  installer, stdout'u dogrudan Inno'nun pipe'i uzerinden yakalar; araya baska
  bir surecin degistirebilecegi karar dosyasi girmez. }
function PathSddl(const Path: string; var Sddl: string): Boolean;
var
  QuotedPath, Params: string;
  Code: Integer;
  Output: TExecOutput;
begin
  Result := False;
  Sddl := '';
  QuotedPath := Path;
  StringChangeEx(QuotedPath, '''', '''''', True);
  Params := '-NoProfile -NonInteractive -Command "$ErrorActionPreference='
          + '''Stop''; $a = Get-Acl -LiteralPath ''' + QuotedPath + ''';'
          + ' [Console]::Out.Write($a.Sddl)"';
  try
    if not ExecAndCaptureOutput(
      ExpandConstant('{sys}\WindowsPowerShell\v1.0\powershell.exe'),
      Params, '', SW_SHOWNORMAL, ewWaitUntilTerminated, Code, Output) then exit;
  except
    Log('KJ Des: ACL ciktisi yakalanamadi: ' + GetExceptionMessage);
    exit;
  end;
  if (Code <> 0) or Output.Error then exit;
  if Trim(CapturedLinesText(Output.StdErr)) <> '' then exit;
  Sddl := Trim(CapturedLinesText(Output.StdOut));
  Result := Sddl <> '';
end;

{ ===== KJDES SAFE TARGET BEGIN ===== }
{ HIGHEST yetkili gorevin hedefi olabilecek yolun BAGIMSIZ dogrulamasi.

  `FileExists` bir guvenlik kontrolu DEGILDIR: custom /DIR=, onceki kurulumdan
  devralinan dizin, gevsek ACL veya junction uzerinden kullanici-yazilabilir bir
  KJDes.exe de "var"dir. Standart kullanici o dosyayi kendi yuku ile
  degistirirse her oturum acilista UAC'siz, KALICI yetki yukseltmesi elde eder.

  Bu blok app/core/failsafe.py::path_is_verified_install ile AYNI olcutleri
  uygular: canonical yol, gercek Program Files koku, zincirde reparse point yok,
  dosya VE ust dizinde yalnizca ayricalikli principal'lar yazma/silme/ACL hakki
  tutuyor, sahip ayricalikli. Herhangi bir okuma hatasinda FAIL CLOSED. }
const
  { Dosyayi DEGISTIRMEYE veya izinlerini ele gecirmeye yarayan haklar:
    WRITE_DATA|APPEND|WRITE_EA|DELETE_CHILD|WRITE_ATTRIBUTES
    |DELETE|WRITE_DAC|WRITE_OWNER|GENERIC_ALL|GENERIC_WRITE }
  DANGEROUS_RIGHTS = $500D0156;

function SidIsTrustedWriter(const Sid: string): Boolean;
begin
  Result := (Sid = 'SY') or (Sid = 'S-1-5-18')            { SYSTEM }
         or (Sid = 'BA') or (Sid = 'S-1-5-32-544')        { Administrators }
         or (Sid = 'CO') or (Sid = 'S-1-3-0')             { CREATOR OWNER }
         or (Sid = 'S-1-5-80-956008885-3418522649-1831038044-1853292631-2271478464');
end;

function SidIsTrustedOwner(const Sid: string): Boolean;
begin
  { Sahip DACL'i her zaman degistirebilir; CREATOR OWNER bir sahip degeri
    DEGILDIR ve burada kabul EDILMEZ. }
  Result := (Sid = 'SY') or (Sid = 'S-1-5-18')
         or (Sid = 'BA') or (Sid = 'S-1-5-32-544')
         or (Sid = 'S-1-5-80-956008885-3418522649-1831038044-1853292631-2271478464');
end;

function HexToCardinal(const S: string; var Value: Cardinal): Boolean;
var
  I, D: Integer;
  C: string;
begin
  Result := False;
  Value := 0;
  if (Length(S) = 0) or (Length(S) > 8) then exit;
  for I := 1 to Length(S) do begin
    C := Uppercase(Copy(S, I, 1));
    if (C >= '0') and (C <= '9') then D := Ord(C[1]) - Ord('0')
    else if (C >= 'A') and (C <= 'F') then D := Ord(C[1]) - Ord('A') + 10
    else exit;
    Value := (Value * 16) + Cardinal(D);
  end;
  Result := True;
end;

{ SDDL hak kisaltmasi -> erisim maskesi. TANIMADIGIMIZ hicbir kisaltma
  yok sayilmaz; cozumleme basarisiz olur ve cagiran FAIL CLOSED davranir. }
function RightsPairMask(const Pair: string; var Mask: Cardinal): Boolean;
begin
  Result := True;
  if      Pair = 'GA' then Mask := $10000000
  else if Pair = 'GX' then Mask := $20000000
  else if Pair = 'GW' then Mask := $40000000
  else if Pair = 'GR' then Mask := $80000000
  else if Pair = 'SD' then Mask := $00010000
  else if Pair = 'RC' then Mask := $00020000
  else if Pair = 'WD' then Mask := $00040000
  else if Pair = 'WO' then Mask := $00080000
  else if Pair = 'FA' then Mask := $001F01FF
  else if Pair = 'FR' then Mask := $00120089
  else if Pair = 'FW' then Mask := $00120116
  else if Pair = 'FX' then Mask := $001200A0
  else if Pair = 'CC' then Mask := $00000001
  else if Pair = 'DC' then Mask := $00000002
  else if Pair = 'LC' then Mask := $00000004
  else if Pair = 'SW' then Mask := $00000008
  else if Pair = 'RP' then Mask := $00000010
  else if Pair = 'WP' then Mask := $00000020
  else if Pair = 'DT' then Mask := $00000040
  else if Pair = 'LO' then Mask := $00000080
  else if Pair = 'CR' then Mask := $00000100
  else begin
    Mask := 0;
    Result := False;
  end;
end;

function SddlRightsMask(const Token: string; var Mask: Cardinal): Boolean;
var
  I: Integer;
  Bit: Cardinal;
begin
  Result := False;
  Mask := 0;
  if Token = '' then exit;
  if Copy(Token, 1, 2) = '0X' then begin
    Result := HexToCardinal(Copy(Token, 3, Length(Token)), Mask);
    exit;
  end;
  if (Length(Token) mod 2) <> 0 then exit;
  I := 1;
  while I < Length(Token) do begin
    if not RightsPairMask(Copy(Token, I, 2), Bit) then exit;
    Mask := Mask or Bit;
    I := I + 2;
  end;
  Result := True;
end;

{ ACE bayraklari IKI KARAKTERLIK belirteclerden olusur. Duz alt-dizgi aramasi
  ('OI'+'OI' -> "OIOI") yanlislikla 'IO' bulur; bu yuzden cift cift gezilir. }
function AceHasFlag(const Flags, Flag: string): Boolean;
var
  I: Integer;
begin
  Result := False;
  if (Length(Flags) mod 2) <> 0 then exit;
  I := 1;
  while I < Length(Flags) do begin
    if Copy(Flags, I, 2) = Flag then begin
      Result := True;
      exit;
    end;
    I := I + 2;
  end;
end;

function SplitAce(const Ace: string; var Fields: TArrayOfString): Boolean;
var
  I, N, Start: Integer;
begin
  SetArrayLength(Fields, 6);
  N := 0;
  Start := 1;
  for I := 1 to Length(Ace) do begin
    if Ace[I] = ';' then begin
      if N >= 6 then begin Result := False; exit; end;
      Fields[N] := Copy(Ace, Start, I - Start);
      N := N + 1;
      Start := I + 1;
    end;
  end;
  if N <> 5 then begin Result := False; exit; end;
  Fields[5] := Copy(Ace, Start, Length(Ace) - Start + 1);
  Result := True;
end;

{ Donus False = ACE cozumlenemedi (FAIL CLOSED).
  Ok=False = bu ACE dusuk yetkili bir principal'a tehlikeli hak veriyor. }
function AceIsHarmless(const Ace: string; var Ok: Boolean): Boolean;
var
  Fields: TArrayOfString;
  Mask: Cardinal;
  AceType, Flags: string;
begin
  Result := False;
  Ok := True;
  if not SplitAce(Ace, Fields) then exit;
  AceType := Uppercase(Trim(Fields[0]));
  Flags := Uppercase(Trim(Fields[1]));
  { DENY ACE'leri bilincli olarak YOK SAYILIR: bir deny yalnizca izni
    DARALTABILIRDI, hesaba katmamak bizi daha KATI yapar. }
  if AceType = 'D' then begin Result := True; exit; end;
  if AceType <> 'A' then exit;             { taninmayan ACE turu -> fail closed }
  { INHERIT_ONLY: bu nesneye uygulanmaz. }
  if AceHasFlag(Flags, 'IO') then begin Result := True; exit; end;
  if not SddlRightsMask(Uppercase(Trim(Fields[2])), Mask) then exit;
  if (Mask and DANGEROUS_RIGHTS) = 0 then begin Result := True; exit; end;
  Ok := SidIsTrustedWriter(Uppercase(Trim(Fields[5])));
  Result := True;
end;

{ Donus False = DACL cozumlenemedi. Ok=False = guvensiz. }
function AclWritersAreTrusted(const Dacl: string; var Ok: Boolean): Boolean;
var
  I, Depth, Start: Integer;
begin
  Result := False;
  Ok := True;
  Depth := 0;
  Start := 0;
  for I := 1 to Length(Dacl) do begin
    if Dacl[I] = '(' then begin
      if Depth <> 0 then exit;
      Depth := 1;
      Start := I + 1;
    end else if Dacl[I] = ')' then begin
      if Depth <> 1 then exit;
      Depth := 0;
      if not AceIsHarmless(Copy(Dacl, Start, I - Start), Ok) then exit;
      if not Ok then begin Result := True; exit; end;
    end;
  end;
  if Depth <> 0 then exit;
  Result := True;
end;

{ 'O:' / 'D:' bolumunu ayiklar. Bolum sonu, PARANTEZ DISINDA gecen bir
  sonraki 'O:'/'G:'/'D:'/'S:' basligidir. }
function SddlSection(const Sddl, Tag: string; var Value: string): Boolean;
var
  I, P, Q, Depth: Integer;
  Rest, C: string;
begin
  Result := False;
  Value := '';
  P := Pos(Tag, Sddl);
  if P = 0 then exit;
  Rest := Copy(Sddl, P + 2, Length(Sddl) - P - 1);
  Depth := 0;
  Q := 0;
  for I := 1 to Length(Rest) do begin
    C := Copy(Rest, I, 1);
    if C = '(' then Depth := Depth + 1
    else if C = ')' then Depth := Depth - 1
    else if (Depth = 0) and (I < Length(Rest)) and (Copy(Rest, I + 1, 1) = ':')
            and ((C = 'O') or (C = 'G') or (C = 'D') or (C = 'S')) then begin
      Q := I;
      break;
    end;
  end;
  if Q > 0 then Value := Copy(Rest, 1, Q - 1) else Value := Rest;
  Value := Trim(Value);
  Result := True;
end;

function LocationIsAclProtected(const Path: string; var Reason: string): Boolean;
var
  Sddl, Owner, Dacl: string;
  Ok: Boolean;
begin
  Result := False;
  if not PathSddl(Path, Sddl) then begin
    Reason := 'guvenlik tanimlayicisi okunamadi: ' + Path;
    exit;
  end;
  if not SddlSection(Sddl, 'O:', Owner) then begin
    Reason := 'SDDL sahibi cozulemedi: ' + Path;
    exit;
  end;
  if not SidIsTrustedOwner(Uppercase(Trim(Owner))) then begin
    Reason := 'nesne sahibi ayricalikli degil (' + Owner + '): ' + Path;
    exit;
  end;
  if not SddlSection(Sddl, 'D:', Dacl) then begin
    Reason := 'SDDL DACL cozulemedi: ' + Path;
    exit;
  end;
  if not AclWritersAreTrusted(Dacl, Ok) then begin
    Reason := 'DACL cozumlenemedi (fail closed): ' + Path;
    exit;
  end;
  if not Ok then begin
    Reason := 'dusuk yetkili principal yazma/silme/ACL hakki tutuyor: ' + Path;
    exit;
  end;
  Result := True;
end;

function PathIsUnderRoot(const Canon: string;
                         const Roots: TArrayOfString): Boolean;
var
  I: Integer;
  Root: string;
begin
  Result := False;
  for I := 0 to GetArrayLength(Roots) - 1 do begin
    Root := Roots[I] + '\';
    { Metinsel onek benzeri ('C:\Program Files Sahte\...') buradan GECEMEZ:
      ayirici ile birlikte karsilastirilir. }
    if CompareText(Copy(Canon, 1, Length(Root)), Root) = 0 then begin
      Result := True;
      exit;
    end;
  end;
end;

function ChainIsReparseFree(const Path: string; var Reason: string): Boolean;
var
  Cur, Prev: string;
  IsRep: Boolean;
begin
  Result := False;
  Cur := Path;
  while Trim(Cur) <> '' do begin
    if not PathIsReparse(Cur, IsRep) then begin
      Reason := 'reparse point durumu okunamadi: ' + Cur;
      exit;
    end;
    if IsRep then begin
      Reason := 'yol zincirinde junction/symlink var: ' + Cur;
      exit;
    end;
    Prev := Cur;
    Cur := ExtractFileDir(Cur);
    if CompareText(Cur, Prev) = 0 then break;
    if Length(Cur) <= 2 then break;
  end;
  Result := True;
end;

{ Verilen EXE, ONLOGON + HIGHEST goreve baglanabilecek kadar korunuyor mu? }
function PathIsVerifiedInstall(const Exe: string; var Reason: string): Boolean;
var
  Canon: string;
  Roots: TArrayOfString;
begin
  Result := False;
  Reason := '';
  if not PathCanonical(Exe, Canon) then begin
    Reason := 'yol canonical hale getirilemedi veya mevcut degil: ' + Exe;
    exit;
  end;
  if not ProgramFilesRoots(Roots) then begin
    Reason := 'gercek Program Files kokleri okunamadi';
    exit;
  end;
  if not PathIsUnderRoot(Canon, Roots) then begin
    Reason := 'hedef gercek Program Files altinda degil: ' + Canon;
    exit;
  end;
  if not ChainIsReparseFree(Canon, Reason) then exit;
  if not LocationIsAclProtected(Canon, Reason) then exit;
  if not LocationIsAclProtected(ExtractFileDir(Canon), Reason) then exit;
  Result := True;
end;
{ ===== KJDES SAFE TARGET END ===== }

{ ─────────────────────────────────────────────────────────────────────────
  Logon failsafe gorevi — kurulum/guncelleme gecisi (F2 kapanisi)

  SORUN: postinstall "KJ Des'i baslat" adimi ISTEGE BAGLI ve silent kurulumda
  atlanir. Kullanici yeni surumu hic calistirmadan oturumu kapatirsa, ONCEKI
  surumden kalmis ve YAZILABILIR bir hedefi gosteren kurtarma gorevi
  bir sonraki logon'da HIGHEST yetkiyle calisirdi.

  GUNCEL MODEL: gorev KALICI DEGILDIR. Yalnizca KJ Des'in isaretli hosts
  yonlendirmesi aktif olabilecegi surece var olur; uygulama yonlendirmeyi
  yazmadan hemen once kurar, temizledigi anda kaldirir. Kurulum, hosts
  DOGRULANMIS bicimde temizse GOREV OLUSTURMAZ; yalnizca yonlendirme
  temizlenemediginde DOGRULANMIS hedefe guvenli bir kurtarma gorevi kurar.

  COZUM (her normal / upgrade / silent kurulumda, secenege BAGLI OLMADAN):
    1. Onceki surumden kalmis olabilecek isaretli hosts blogu TEMIZLENIR.
       Gorev ancak yonlendirme gercekten yoksa gereksizdir; korlemesine
       silinirse temizlenmemis bir yonlendirme temizleyicisiz kalirdi.
    2. Gorev(ler) hosts SONUCUNA ve KAYITLI HEDEFE gore uzlastirilir
       (ReconcileFailsafeTask). hosts temizlenemediyse gorev korlemesine
       KORUNMAZ: hedefi okunur, dogrulanir; yalnizca korumali
       <app>\KJ Des.exe --cleanup-hosts hedefi korunabilir, digerleri guvenli
       gorevle DEGISTIRILIR.
    3. Basarisizlik SESSIZCE YUTULMAZ: Setup log'una yazilir, etkilesimli
       kurulumda hata kutusu gosterilir ve kurulum RaiseException ile
       basarisiz olur (silent upgrade'de de sifir-disi cikis kodu).
  ───────────────────────────────────────────────────────────────────────── }

function TaskExists(const Name: string): Boolean;
var
  Code: Integer;
begin
  Result := False;
  if Exec(ExpandConstant('{cmd}'),
          '/C schtasks /Query /TN "' + Name + '" >nul 2>&1',
          '', SW_HIDE, ewWaitUntilTerminated, Code) then
    Result := (Code = 0);
end;

{ ── Gorev katmani ILKELLERI ───────────────────────────────────────────────
  Asagidaki isaretli KARAR blogu yalnizca bu uc rutini kullanir. Testler ayni
  karar blogunu ayiklayip SAHTE ilkellerle derleyip calistirir; boylece mantik
  gercek schtasks'a dokunmadan dogrulanir. }

{ Gorevi siler ve /Query ile GERCEKTEN gittigini dogrular.
  Gorev zaten yoksa True (silinecek bir sey yok; schtasks bu durumda sifir-disi
  kod dondurur, bu bir HATA DEGILDIR). }
function TaskDeleteVerified(const Name: string): Boolean;
var
  Code: Integer;
begin
  if not TaskExists(Name) then begin
    Result := True;
    exit;
  end;
  Exec(ExpandConstant('{cmd}'),
       '/C schtasks /Delete /TN "' + Name + '" /F >nul 2>&1',
       '', SW_HIDE, ewWaitUntilTerminated, Code);
  Result := not TaskExists(Name);
end;

{ Gorevin TAM tanimini XML olarak dondurur.
  Donus False = gorev yok VEYA tanim okunamadi/bozuk (ikisi de ayni sonuca
  goturur: guvenli sayilmaz). Tek tek alan okumak yerine TUM tanim dondurulur;
  dogrulamayi karar blogu yapar (bkz. TaskDefinitionIsSafe): boylece ikinci bir
  <Exec> eylemi veya yinelenmis <Command> gizlenemez.
  XML dili notrdur; /FO LIST ciktisi YERELLESTIGI icin kullanilmaz.
  GUVENLIK: XML kullanici-yazilabilir TEMP dosyasina yonlendirilmez; schtasks
  stdout'u dogrudan Inno pipe'iyle yakalanir ve ayni bellek degeri dogrulanir. }
function TaskQueryXml(const Name: string; var Xml: string): Boolean;
var
  Code: Integer;
  Output: TExecOutput;
begin
  Result := False;
  Xml := '';
  try
    if not ExecAndCaptureOutput(
      ExpandConstant('{sys}\schtasks.exe'),
      '/Query /TN "' + Name + '" /XML',
      '', SW_SHOWNORMAL, ewWaitUntilTerminated, Code, Output) then exit;
  except
    Log('KJ Des: gorev XML ciktisi yakalanamadi: ' + GetExceptionMessage);
    exit;
  end;
  if (Code <> 0) or Output.Error then exit;
  if Trim(CapturedLinesText(Output.StdErr)) <> '' then exit;
  Xml := CapturedLinesText(Output.StdOut);
  Result := Trim(Xml) <> '';
end;

{ ONLOGON + HIGHEST gorevi olusturur. cmd.exe ARACILIGI OLMADAN calistirilir:
  ic tirnaklarin cmd tarafindan yeniden yorumlanmasi engellenir. }
function TaskCreateLogon(const Name, Exe, Args: string): Boolean;
var
  Code: Integer;
begin
  Result := Exec(ExpandConstant('{sys}\schtasks.exe'),
    '/Create /TN "' + Name + '" /TR "\"' + Exe + '\" ' + Args
    + '" /SC ONLOGON /RL HIGHEST /F',
    '', SW_HIDE, ewWaitUntilTerminated, Code) and (Code = 0);
end;

{ ===== KJDES FAILSAFE TASK BEGIN ===== }
{ Gorev yasam dongusunun TEK karar noktasi (installer tarafi).

  Kural: ONLOGON + HIGHEST bir gorev, YALNIZCA korumali kurulum hedefini
  (<app>\KJ Des.exe --cleanup-hosts) gosterebilir. Kullanici-yazilabilir,
  okunamayan, bozuk veya yanlis argumanli hicbir tanim ayakta BIRAKILMAZ -
  hosts temizligi basarisiz olsa bile. Aksi halde standart kullanici, her
  oturum acilista YUKSEK yetkiyle calisan bir hedefi degistirerek kalici,
  UAC'siz yetki yukseltmesi elde ederdi.

  Bu blok yalnizca TaskQuery / TaskDeleteVerified / TaskCreateLogon
  ilkellerine baglidir; testler ayni kodu sahte ilkellerle calistirir. }
const
  TASK_NAME       = 'KJDesHostsFailsafe';
  { KJ Des has no legacy task names; other products' tasks (DPort's
    DPortHostsFailsafe / DiscordConnectHostsFailsafe) are never touched. }
  LEGACY_TASK     = '';
  FS_CLEANUP_ARGS = '--cleanup-hosts';

function CountOccurrences(const Haystack, Needle: string): Integer;
var
  P, Start: Integer;
begin
  Result := 0;
  if (Needle = '') or (Haystack = '') then exit;
  Start := 1;
  while Start <= Length(Haystack) do begin
    P := Pos(Needle, Copy(Haystack, Start, Length(Haystack) - Start + 1));
    if P = 0 then exit;
    Result := Result + 1;
    Start := Start + P + Length(Needle) - 1;
  end;
end;

{ Etiketin TAM OLARAK BIR kez gectigini dogrular ve degerini dondurur.
  Yinelenmis etiket (or. iki <Command>) REDDEDILIR; "son goruleni al"
  davranisi, once zararli sonra masum gorunen bir tanimi guvenli gosterirdi. }
function ExtractSingleTag(const Xml, Tag: string; var Value: string): Boolean;
var
  OpenT, CloseT: string;
  P, Q: Integer;
begin
  Result := False;
  Value := '';
  OpenT := '<' + Tag + '>';
  CloseT := '</' + Tag + '>';
  if CountOccurrences(Xml, OpenT) <> 1 then exit;
  if CountOccurrences(Xml, CloseT) <> 1 then exit;
  P := Pos(OpenT, Xml) + Length(OpenT);
  Q := Pos(CloseT, Xml);
  if Q <= P then exit;
  Value := Trim(Copy(Xml, P, Q - P));
  Result := True;
end;

{ XML entity cozumu. YALNIZCA bes standart adlandirilmis entity desteklenir;
  sayisal (&#65;) veya bilinmeyen entity FAIL CLOSED'dur. Boylece ayni girdi
  her zaman ayni sonucu verir (deterministik). }
function XmlDecode(const S: string; var Decoded: string): Boolean;
var
  I, P, Found: Integer;
  Ent, C: string;
begin
  Result := False;
  Decoded := '';
  I := 1;
  while I <= Length(S) do begin
    C := Copy(S, I, 1);
    if C <> '&' then begin
      Decoded := Decoded + C;
      I := I + 1;
    end else begin
      Found := 0;
      P := I + 1;
      while (P <= Length(S)) and (P <= I + 8) do begin
        if Copy(S, P, 1) = ';' then begin
          Found := P;
          break;
        end;
        P := P + 1;
      end;
      if Found = 0 then exit;
      Ent := Lowercase(Copy(S, I, Found - I + 1));
      if Ent = '&amp;' then Decoded := Decoded + '&'
      else if Ent = '&lt;' then Decoded := Decoded + '<'
      else if Ent = '&gt;' then Decoded := Decoded + '>'
      else if Ent = '&quot;' then Decoded := Decoded + '"'
      else if Ent = '&apos;' then Decoded := Decoded + ''''
      else exit;
      I := Found + 1;
    end;
  end;
  Result := True;
end;

{ Gorevin TAM tanimi beklenen guvenli tanim mi?

  Kabul icin HEPSI gerekli:
    - tam olarak BIR <Exec> eylemi (baska eylem turu hic yok)
    - tam olarak BIR <Command> ve BIR <Arguments>
    - tam olarak BIR trigger, o da <LogonTrigger>
    - <RunLevel> = HighestAvailable
    - Command (entity cozulmus) = korumali kurulum hedefi
    - Arguments (entity cozulmus) = --cleanup-hosts
  Eksik, fazladan, bozuk veya okunamayan tanim REDDEDILIR. }
function TaskDefinitionIsSafe(const Xml, SafeExe: string): Boolean;
var
  Value, Decoded: string;
begin
  Result := False;
  if Trim(Xml) = '' then exit;

  { Tam olarak bir Exec eylemi; baska eylem turu kabul edilmez. }
  if CountOccurrences(Xml, '<Exec>') <> 1 then exit;
  if CountOccurrences(Xml, '</Exec>') <> 1 then exit;
  if CountOccurrences(Xml, '<ComHandler') > 0 then exit;
  if CountOccurrences(Xml, '<SendEmail') > 0 then exit;
  if CountOccurrences(Xml, '<ShowMessage') > 0 then exit;

  { Tam olarak bir trigger, o da ONLOGON. ('Trigger>' sayisi = ac + kapa) }
  if CountOccurrences(Xml, '<LogonTrigger>') <> 1 then exit;
  if CountOccurrences(Xml, 'Trigger>') <> 2 then exit;

  { Yetki seviyesi }
  if not ExtractSingleTag(Xml, 'RunLevel', Value) then exit;
  if CompareText(Value, 'HighestAvailable') <> 0 then exit;

  { Hedef }
  if not ExtractSingleTag(Xml, 'Command', Value) then exit;
  if not XmlDecode(Value, Decoded) then exit;
  if CompareText(Trim(RemoveQuotes(Trim(Decoded))), Trim(SafeExe)) <> 0 then exit;

  { Argumanlar }
  if not ExtractSingleTag(Xml, 'Arguments', Value) then exit;
  if not XmlDecode(Value, Decoded) then exit;
  Result := CompareText(Trim(RemoveQuotes(Trim(Decoded))), FS_CLEANUP_ARGS) = 0;
end;

{ Kayitli gorev, korumali kurulum hedefiyle BIREBIR esliyor mu?
  Gorev yoksa veya tanimi okunamiyorsa False (fail closed). }
function FailsafeTaskIsSafe(const SafeExe: string): Boolean;
var
  Xml: string;
begin
  Result := False;
  if not TaskQueryXml(TASK_NAME, Xml) then exit;
  Result := TaskDefinitionIsSafe(Xml, SafeExe);
end;

{ Donus: "ayakta guvensiz gorev yok" GARANTI edilebiliyor mu.
  False ise Problem doludur ve cagiran bunu SESSIZCE YUTMAMALIDIR. }
function ReconcileFailsafeTask(HostsCleaned: Boolean; const SafeExe: string;
                               var Problem: string): Boolean;
var
  Reason: string;
begin
  Problem := '';
  Reason := '';
  Result := False;

  { 1) Eski adlar hosts sonucundan BAGIMSIZ olarak HER ZAMAN kaldirilir:
       onlarin hedefi bizim protokolumuzle dogrulanmaz, dolayisiyla guvenli
       kabul edilemezler. }
  if (LEGACY_TASK <> '') and not TaskDeleteVerified(LEGACY_TASK) then begin
    Problem := 'Eski "' + LEGACY_TASK + '" oturum acilis gorevi kaldirilamadi.';
    exit;
  end;

  { 2) hosts temizligi DOGRULANDI -> kurtarilacak yonlendirme yok, gorev de
       gereksiz. }
  if HostsCleaned then begin
    if not TaskDeleteVerified(TASK_NAME) then begin
      Problem := '"' + TASK_NAME + '" gorevi kaldirilamadi.';
      exit;
    end;
    Result := True;
    exit;
  end;

  { 3) hosts kalintisi VAR -> kurtarma gorevi GEREKLI. Ama once HEDEFIN KENDISI
       bagimsiz olarak dogrulanmali: dogrulanmamis bir EXE ne goreve hedef
       yapilir ne de ona isaret eden bir gorev korunur. `FileExists` burada
       kullanilmaz; kullanici-yazilabilir bir KJDes.exe de "vardir". }
  if not PathIsVerifiedInstall(SafeExe, Reason) then begin
    { Guvensiz hedefe isaret ediyor olabilecek gorev ayakta BIRAKILMAZ. }
    if not TaskDeleteVerified(TASK_NAME) then
      Problem := 'Kurulum hedefi dogrulanamadi (' + Reason
                 + ') VE mevcut oturum acilis gorevi kaldirilamadi.'
    else
      Problem := 'Kurulum hedefi HIGHEST gorev icin dogrulanamadi: ' + Reason;
    exit;
  end;

  { 4) Ayakta olan TAM tanim beklenen guvenli tanimsa korunur. }
  if FailsafeTaskIsSafe(SafeExe) then begin
    Log('KJ Des FAILSAFE: mevcut gorev korumali hedefi gosteriyor, KORUNDU');
    Result := True;
    exit;
  end;

  { 5) Eksik / okunamayan / bozuk / fazladan eylemli / yanlis argumanli:
       once KALDIR, sonra DOGRULANMIS hedefle YENIDEN kur. }
  Log('KJ Des FAILSAFE: gorev dogrulanamadi -> guvenli hedefle DEGISTIRILIYOR');
  if not TaskDeleteVerified(TASK_NAME) then begin
    Problem := 'Guvenilmeyen "' + TASK_NAME + '" gorevi kaldirilamadi.';
    exit;
  end;
  if not TaskCreateLogon(TASK_NAME, SafeExe, FS_CLEANUP_ARGS) then begin
    Problem := 'Guvenli kurtarma gorevi olusturulamadi.';
    exit;
  end;

  { 6) GERI OKUMA: gercek tanim yeniden okunur ve AYNI kontrollerden gecirilir. }
  if not FailsafeTaskIsSafe(SafeExe) then begin
    TaskDeleteVerified(TASK_NAME);
    Problem := 'Olusturulan kurtarma gorevi geri okundugunda DOGRULANAMADI.';
    exit;
  end;
  Result := True;
end;
{ ===== KJDES FAILSAFE TASK END ===== }

procedure DropFailsafeTaskAfterHostsCleanup();
var
  HostsCleaned: Boolean;
  SafeExe, Problem: string;
begin
  { 1) Onceki surumden kalmis isaretli hosts blogunu temizle. }
  HostsCleaned := CleanHostsBlock(HostsFilePath());
  if not HostsCleaned then
    Log('KJ Des FAILSAFE: hosts yonlendirmesi temizlenemedi/dogrulanamadi -> '
        + 'guvenli kurtarma gorevi GEREKLI');

  { 2) Hedefin GUVENLI olup olmadigina ReconcileFailsafeTask karar verir; oradaki
       PathIsVerifiedInstall canonical yolu, gercek Program Files kokunu,
       reparse point'siz zinciri ve ACL/sahiplik durumunu dogrular. Burada
       `FileExists` gibi bir "guvenlik" kapisi YOKTUR: dosyanin var olmasi onu
       guvenli YAPMAZ (var olmamasi da zaten dogrulamayi dusurur). }
  SafeExe := ExpandConstant('{app}\{#MyAppExeName}');
  if ReconcileFailsafeTask(HostsCleaned, SafeExe, Problem) then begin
    { NOT: Bir satir '[' ile BASLAYAMAZ; ISCC bunu bolum etiketi sanar. }
    Log('KJ Des: failsafe gorev uzlasmasi TAMAM (hosts temiz='
        + IntToStr(Integer(HostsCleaned)) + ')');
    if not HostsCleaned and not WizardSilent then
      MsgBox('KJ Des kuruldu, ancak hosts dosyasindaki eski Discord'
             + ' yonlendirmesi temizlenemedi.' + #13#10#13#10
             + 'Guvenli bir oturum acilis temizlik gorevi kuruldu:'
             + ' yonlendirme bir sonraki oturum acilisinda otomatik'
             + ' temizlenecek.' + #13#10#13#10
             + 'Isterseniz KJ Des''i calistirip "Restore defaults / Varsayilana Don" ile hemen'
             + ' temizleyebilirsiniz.', mbInformation, MB_OK);
    exit;
  end;

  { 2) Guvenlik garantisi verilemedi: SESSIZCE BASARILI SAYMA.
       Etkilesimli kurulumda aciklayici kutu, her kurulumda (silent dahil)
       RaiseException ile gorunur basarisizlik + sifir-disi cikis kodu. }
  Log('KJ Des FAILSAFE HATASI: ' + Problem);
  if not WizardSilent then
    MsgBox('KJ Des guvenli kurtarma gorevini kuramadi:' + #13#10#13#10
           + Problem + #13#10#13#10
           + 'Kurulum guvenlik nedeniyle durduruluyor. Gorev Zamanlayici''da'
           + ' "' + TASK_NAME + '" ve "' + LEGACY_TASK + '" gorevlerini elle'
           + ' silip kurulumu tekrar deneyin.', mbError, MB_OK);
  RaiseException('KJ Des guvenli kurtarma gorevi kurulamadi: ' + Problem);
end;

{ KJ Des pasifse Restart Manager sureci beklemeden zorla kapatabilir. Korumali
  DNS yedegi veya hosts yonlendirmesi varsa normal geri alma tamamlanmadan
  sureci oldurmek yasaktir; kullanici once Varsayilana Don yapar. }
{ What KJ Des still has to restore, one localized line per item ('' = nothing).
  Only KJ Des's own state is inspected: its DNS backup and its marked hosts
  block. An unreadable hosts file counts as "not restored" (fail closed). }
function DnsBackupPresent(): Boolean;
begin
  Result := FileExists(ExpandConstant('{commonappdata}\KJ Des\dns_state.json'));
end;

{ KJ Des's marked hosts block is present, or the hosts file cannot be read
  (fail closed: treated as present). }
function KJDesHostsResidue(): Boolean;
var
  Lines: TArrayOfString;
  HostsPath: string;
begin
  Result := False;
  HostsPath := HostsFilePath();
  if FileExists(HostsPath) then begin
    if not LoadStringsFromFile(HostsPath, Lines) then
      Result := True
    else if HostsHasKJDesResidue(Lines) then
      Result := True;
  end;
end;

function RestoreProblems(): string;
begin
  Result := '';
  if DnsBackupPresent() then
    Result := Result + CustomMessage('ResidueDns') + #13#10;
  if KJDesHostsResidue() then
    Result := Result + CustomMessage('ResidueHosts') + #13#10;
end;

function ConnectionRequiresRestore(): Boolean;
begin
  Result := RestoreProblems() <> '';
end;

{ Restart Manager 30 saniye bekledigi icin pasif KJ Des'i kendimiz kapatiriz.
  Guvenlik sinirlari:
    - Yalniz ACL/reparse/canonical kontrollerinden gecen kurulu hedef kullanilir.
    - WMI sonucunda ExecutablePath bu hedefle BIREBIR eslesen PID'ler kapatilir.
    - Ayni adli kaynak/test KJDes.exe veya baska bir surec ASLA kapatilmaz.
    - Serbest bicimli surec adi/komut satiri shell'e yerlestirilmez. }
function StopVerifiedPassiveKJDes(): Boolean;
var
  SafeExe, Reason, QuotedPath, Params: string;
  Code: Integer;
  Output: TExecOutput;
begin
  Result := False;
  SafeExe := ExpandConstant('{app}\{#MyAppExeName}');

  { Ilk kurulumda kapatilacak kurulu hedef yoktur. }
  if not FileExists(SafeExe) then begin
    Result := True;
    exit;
  end;

  if not PathIsVerifiedInstall(SafeExe, Reason) then begin
    Log('KJ Des: pasif surec kapatma hedefi dogrulanamadi: ' + Reason);
    exit;
  end;

  { Ilk kontrolden sonra kullanici baglantiyi etkinlestirmis olabilir. Zorla
    kapatmaya EN YAKIN noktada durumu yeniden oku. }
  if ConnectionRequiresRestore() then begin
    Log('KJ Des: pasif kapatma oncesi ikinci kontrolde aktif durum algilandi');
    exit;
  end;

  QuotedPath := SafeExe;
  StringChangeEx(QuotedPath, '''', '''''', True);
  Params := '-NoProfile -NonInteractive -Command "$ErrorActionPreference=' +
            '''Stop''; $target=''' + QuotedPath + ''';' +
            ' $all=@(Get-CimInstance Win32_Process -Filter '
            + '''Name=''''KJDes.exe''''''' + ');' +
            ' $mine=@($all | Where-Object {' +
            ' [StringComparer]::OrdinalIgnoreCase.Equals($_.ExecutablePath,$target) });' +
            ' foreach($p in $mine){ Stop-Process -Id $p.ProcessId -Force -ErrorAction Stop };' +
            ' Start-Sleep -Milliseconds 100;' +
            ' $left=@(Get-CimInstance Win32_Process -Filter '
            + '''Name=''''KJDes.exe''''''' + ' | Where-Object {' +
            ' [StringComparer]::OrdinalIgnoreCase.Equals($_.ExecutablePath,$target) });' +
            ' if($left.Count -ne 0){ exit 3 }"';
  try
    if not ExecAndCaptureOutput(
      ExpandConstant('{sys}\WindowsPowerShell\v1.0\powershell.exe'),
      Params, '', SW_HIDE, ewWaitUntilTerminated, Code, Output) then begin
      Log('KJ Des: pasif surec kapatma komutu baslatilamadi');
      exit;
    end;
  except
    Log('KJ Des: pasif surec kapatma hatasi: ' + GetExceptionMessage);
    exit;
  end;
  if (Code <> 0) or Output.Error or
     (Trim(CapturedLinesText(Output.StdErr)) <> '') then begin
    Log('KJ Des: pasif surec kapatma dogrulanamadi; kod=' + IntToStr(Code));
    exit;
  end;
  Log('KJ Des: pasif kurulu surec beklemeden kapatildi/dogrulandi');
  Result := True;
end;

{ ===== KJDES OPTIONAL USER DATA BEGIN ===== }
var
  DeleteUserSettings, DeleteUserLog: Boolean;
  UninstallUserDataPath: string;
  UninstallOptionsAccepted: Boolean;
  UserUninstallUI: Boolean;

function DataOpenDirectory(Name: string; Access, Share: LongWord;
  Security: LongWord; Creation, Flags, Template: LongWord): LongWord;
  external 'CreateFileW@kernel32.dll stdcall';
function DataCloseHandle(Handle: LongWord): Boolean;
  external 'CloseHandle@kernel32.dll stdcall';
function DataLastError(): LongWord;
  external 'GetLastError@kernel32.dll stdcall';

function DeleteSelectedUserData(const DataPath: string; Settings, Logs: Boolean): Boolean;
var
  Canon, Cur, Prev, Target: string;
  Paths: TArrayOfString;
  Handles: array of LongWord;
  I, Count: Integer;
  Handle, Attrs, Error: LongWord;
  IsRep: Boolean;
begin
  Result := False;
  if not Settings and not Logs then begin
    Result := True;
    exit;
  end;
  if not DirExists(DataPath) then begin
    Result := not FileExists(DataPath);
    exit;
  end;
  if not PathCanonical(DataPath, Canon) then exit;
  if CompareText(ExtractFileName(Canon), 'KJ Des') <> 0 then exit;
  { Pin every directory from root to leaf, without FILE_SHARE_DELETE.
    Reparse points are opened themselves and rejected before traversing them.
    This also prevents junction-swap races during the two file deletions. }
  Cur := Canon;
  while Cur <> '' do begin
    Count := GetArrayLength(Paths);
    SetArrayLength(Paths, Count + 1);
    Paths[Count] := Cur;
    Prev := Cur;
    Cur := ExtractFileDir(Cur);
    if (Cur = Prev) or (Length(Cur) <= 2) then break;
  end;
  try
    for I := GetArrayLength(Paths) - 1 downto 0 do begin
      Handle := DataOpenDirectory(Paths[I], 1, 3, 0, 3, $02200000, 0);
      if Handle = $FFFFFFFF then exit;
      Count := GetArrayLength(Handles);
      SetArrayLength(Handles, Count + 1);
      Handles[Count] := Handle;
      if not PathIsReparse(Paths[I], IsRep) then exit;
      if IsRep then exit;
    end;
    Result := True;
    for I := 0 to 1 do begin
      if ((I = 0) and Settings) or ((I = 1) and Logs) then begin
      if I = 0 then Target := AddBackslash(Canon) + 'config.json'
      else Target := AddBackslash(Canon) + 'kjdes.log';
      Attrs := GetFileAttributesW(Target);
      if Attrs = $FFFFFFFF then begin
        Error := DataLastError();
        if (Error <> 2) and (Error <> 3) then Result := False;
      end else begin
        if not PathIsReparse(Target, IsRep) then Result := False
        else if IsRep or DirExists(Target) then Result := False
        else if not DeleteFile(Target) then Result := False;
        if GetFileAttributesW(Target) <> $FFFFFFFF then Result := False;
      end;
    end;
    end;
  finally
    for I := GetArrayLength(Handles) - 1 downto 0 do
      DataCloseHandle(Handles[I]);
  end;
end;
{ ===== KJDES OPTIONAL USER DATA END ===== }

procedure CleanupUninstallCache();
var
  Root, Cache, Reason, Name, VersionPart: string;
  Entry: TFindRec;
  I: Integer;
  ValidName: Boolean;
begin
  Root := ExpandConstant('{commonappdata}\KJ Des');
  Cache := Root + '\updates';
  { Machine cache must be administrator-owned and reparse-free. No recursive
    deletion: unknown files, subdirectories and recovery state are preserved. }
  if DirExists(Cache) then begin
    if not ChainIsReparseFree(Cache, Reason) or
       not LocationIsAclProtected(Root, Reason) or
       not LocationIsAclProtected(Cache, Reason) then begin
      Log('KJ Des: guncelleme onbellegi guvenle temizlenemedi: ' + Reason);
      exit;
    end;
    if FindFirst(Cache + '\KJDes-Setup-*.exe', Entry) then begin
      try
        repeat
          Name := Entry.Name;
          VersionPart := Copy(Name, 13, Length(Name) - 16);
          ValidName := (VersionPart <> '') and
            (CompareText(Copy(Name, 1, 12), 'KJDes-Setup-') = 0);
          for I := 1 to Length(VersionPart) do
            if Pos(Copy(VersionPart, I, 1), '0123456789.') = 0 then ValidName := False;
          if ValidName and ((Entry.Attributes and $410) = 0) then
            if not DeleteFile(Cache + '\' + Name) then
              Log('KJ Des: eski kurulum paketi silinemedi: ' + Name);
        until not FindNext(Entry);
      finally FindClose(Entry); end;
    end;
    RemoveDir(Cache); { succeeds only when empty }
  end;
  if DirExists(Root) and ChainIsReparseFree(Root, Reason) and
     LocationIsAclProtected(Root, Reason) then RemoveDir(Root);
  { Remove only an empty, non-redirected user folder after an explicit choice. }
  if (DeleteUserSettings or DeleteUserLog) and DirExists(UninstallUserDataPath) and
     ChainIsReparseFree(UninstallUserDataPath, Reason) then
    RemoveDir(UninstallUserDataPath);
end;

function InitializeUninstall(): Boolean;
var
  RelaunchCode: Integer;
  Problems: string;
begin
  Result := False;
  DeleteUserSettings := False;
  DeleteUserLog := False;
  { InitializeUninstall precedes Inno's built-in confirmation. Direct launches
    hand off once to the SAME uninstaller with our explicit consent page.
    Never use /VERYSILENT: no files may be removed without that page. }
  if not UninstallSilent then begin
    if not ShellExec('open', ExpandConstant('{uninstallexe}'),
      '/SILENT /KJDESUI=1 /NORESTART', '', SW_SHOWNORMAL, ewNoWait, RelaunchCode) then
      MsgBox(CustomMessage('UninstallUiFailed'), mbError, MB_OK);
    exit;
  end;
  UserUninstallUI := (not UninstallSilent) or (ExpandConstant('{param:KJDESUI|0}') = '1');
  UninstallOptionsAccepted := not UserUninstallUI;
  UninstallUserDataPath := ExpandConstant('{userappdata}\KJ Des');
  Problems := RestoreProblems();
  if Problems <> '' then begin
    Log('KJ Des: uninstall blocked, restoration incomplete: ' + Problems);
    if UserUninstallUI then
      MsgBox(FmtMessage(CustomMessage('UninstallNeedsRestore'), [Problems]), mbError, MB_OK);
    exit;
  end;
  Result := StopVerifiedPassiveKJDes();
  if not Result and UserUninstallUI then
    MsgBox(CustomMessage('UninstallCloseFailed'), mbError, MB_OK);
end;

procedure InitializeUninstallProgressForm();
var
  Option, LogOption: TNewCheckBox;
  Note: TNewStaticText;
  ProceedButton, BackButton: TNewButton;
  OldTitle, OldDescription: string;
begin
  if not UserUninstallUI then exit;
  { Reuse the uninstaller's own form, before any file removal. }
  OldTitle := UninstallProgressForm.PageNameLabel.Caption;
  OldDescription := UninstallProgressForm.PageDescriptionLabel.Caption;
  UninstallProgressForm.Height := ScaleY(310);
  UninstallProgressForm.PageNameLabel.Caption := 'KJ Des’i kaldır';
  UninstallProgressForm.PageDescriptionLabel.Caption := 'KJ Des bu bilgisayardan kaldırılacak.';
  UninstallProgressForm.ProgressBar.Visible := False;
  UninstallProgressForm.StatusLabel.Visible := False;
  UninstallProgressForm.CancelButton.Visible := False;
  Option := TNewCheckBox.Create(UninstallProgressForm);
  LogOption := TNewCheckBox.Create(UninstallProgressForm);
  Note := TNewStaticText.Create(UninstallProgressForm);
  ProceedButton := TNewButton.Create(UninstallProgressForm);
  BackButton := TNewButton.Create(UninstallProgressForm);
  try
    Option.Parent := UninstallProgressForm.InstallingPage;
    Option.SetBounds(UninstallProgressForm.StatusLabel.Left, ScaleY(40),
      UninstallProgressForm.StatusLabel.Width, ScaleY(20));
    Option.Caption := 'Ayarlarımı sil';
    Option.Checked := False;
    LogOption.Parent := Option.Parent;
    LogOption.SetBounds(Option.Left, Option.Top + Option.Height + ScaleY(6),
      Option.Width, Option.Height);
    LogOption.Caption := 'Log kayıtlarımı sil';
    LogOption.Checked := False;
    Note.Parent := Option.Parent;
    Note.AutoSize := False;
    Note.WordWrap := True;
    Note.SetBounds(Option.Left, ScaleY(4), Option.Width, ScaleY(30));
    Note.Caption := 'İsterseniz aşağıdaki verileri de silebilirsiniz. Seçmedikleriniz korunur.';
    Option.Hint := UninstallUserDataPath + '\config.json';
    Option.ShowHint := True;
    LogOption.Hint := UninstallUserDataPath + '\kjdes.log';
    LogOption.ShowHint := True;
    ProceedButton.Parent := UninstallProgressForm;
    ProceedButton.SetBounds(UninstallProgressForm.CancelButton.Left - ScaleX(90),
      UninstallProgressForm.CancelButton.Top, ScaleX(80), UninstallProgressForm.CancelButton.Height);
    ProceedButton.Caption := 'Kaldır';
    ProceedButton.ModalResult := mrOK;
    ProceedButton.Default := True;
    BackButton.Parent := UninstallProgressForm;
    BackButton.SetBounds(UninstallProgressForm.CancelButton.Left,
      UninstallProgressForm.CancelButton.Top, UninstallProgressForm.CancelButton.Width,
      UninstallProgressForm.CancelButton.Height);
    BackButton.Caption := 'İptal';
    BackButton.ModalResult := mrCancel;
    BackButton.Cancel := True;
    UninstallOptionsAccepted := UninstallProgressForm.ShowModal() = mrOK;
    DeleteUserSettings := UninstallOptionsAccepted and Option.Checked;
    DeleteUserLog := UninstallOptionsAccepted and LogOption.Checked;
  finally
    Option.Free;
    LogOption.Free;
    Note.Free;
    ProceedButton.Free;
    BackButton.Free;
    UninstallProgressForm.PageNameLabel.Caption := OldTitle;
    UninstallProgressForm.PageDescriptionLabel.Caption := OldDescription;
    UninstallProgressForm.ProgressBar.Visible := True;
    UninstallProgressForm.StatusLabel.Visible := True;
    UninstallProgressForm.CancelButton.Visible := True;
  end;
end;

{ ===== KJDES UPGRADE DECISION BEGIN ===== }
{ Upgrade over an installation that left ONLY its DNS backup behind (e.g. a
  1.0.1 restore that could not finish, GitHub issue #1). Setup itself never
  reads, changes or deletes the backup or any DNS setting; it only replaces
  the program files so the newer app can run its own startup recovery. }
const
  UPGRADE_PROCEED = 0;        { nothing pending: normal passive-close path }
  UPGRADE_KEEP_BACKUP = 1;    { only the DNS backup is pending, KJ Des not running }
  UPGRADE_BLOCK_ACTIVE = 2;   { KJ Des hosts block present / hosts unreadable }
  UPGRADE_BLOCK_RUNNING = 3;  { backup pending and KJ Des running, or unknown }

function UpgradeDecision(BackupPresent, HostsResidue, RunningKnown, Running: Boolean): Integer;
begin
  if HostsResidue then
    Result := UPGRADE_BLOCK_ACTIVE
  else if not BackupPresent then
    Result := UPGRADE_PROCEED
  else if (not RunningKnown) or Running then
    Result := UPGRADE_BLOCK_RUNNING
  else
    Result := UPGRADE_KEEP_BACKUP;
end;
{ ===== KJDES UPGRADE DECISION END ===== }

{ Is ANY KJDes.exe process running (any path)? The DNS backup is machine-wide,
  so any instance may be working on it. False = the answer is unknown. }
function AnyKJDesRunning(var Running: Boolean): Boolean;
var
  Code: Integer;
begin
  Result := False;
  Running := True;
  if not Exec(ExpandConstant('{sys}\WindowsPowerShell\v1.0\powershell.exe'),
    '-NoProfile -NonInteractive -Command "if (@(Get-Process -Name KJDes -ErrorAction SilentlyContinue).Count -gt 0) { exit 10 } else { exit 20 }"',
    '', SW_HIDE, ewWaitUntilTerminated, Code) then exit;
  if Code = 10 then begin Running := True; Result := True; end
  else if Code = 20 then begin Running := False; Result := True; end;
end;

function PrepareToInstall(var NeedsRestart: Boolean): string;
var
  Known, Running, Backup, Residue: Boolean;
begin
  Result := '';
  Backup := DnsBackupPresent();
  Residue := KJDesHostsResidue();
  Known := False;
  Running := True;
  if Backup and not Residue then
    Known := AnyKJDesRunning(Running);
  case UpgradeDecision(Backup, Residue, Known, Running) of
    UPGRADE_BLOCK_ACTIVE: begin
      Log('KJ Des: hosts yonlendirmesi aktif/okunamadi; kurulum iptal edildi');
      Result := ExpandConstant('{cm:ActiveConnectionBlock}');
      exit;
    end;
    UPGRADE_BLOCK_RUNNING: begin
      Log('KJ Des: DNS yedegi bekliyor ve KJ Des calisiyor/bilinmiyor; kurulum iptal edildi');
      Result := ExpandConstant('{cm:PendingRestoreRunning}');
      exit;
    end;
    UPGRADE_KEEP_BACKUP: begin
      { Nothing runs, nothing is closed; the backup stays for the new app. }
      Log('KJ Des: yalniz DNS yedegi bekliyor, KJ Des calismiyor; yukseltme devam ediyor, yedek korunuyor');
      exit;
    end;
  end;
  if ConnectionRequiresRestore() then begin
    Log('KJ Des: aktif veya bilinmeyen baglanti durumu; zorla kapatma oncesi kurulum iptal edildi');
    Result := ExpandConstant('{cm:ActiveConnectionBlock}');
    exit;
  end;
  if not StopVerifiedPassiveKJDes() then begin
    { Ikinci kontrol aktif durumu yakaladiysa dogru yonlendirmeyi goster. }
    if ConnectionRequiresRestore() then
      Result := ExpandConstant('{cm:ActiveConnectionBlock}')
    else
      Result := ExpandConstant('{cm:PassiveCloseFailed}');
  end;
end;

{ Kisayol/masaustu ikonu bos gorunmesin diye kurulum sonunda shell ikon
  onbellegini yenilenmeye zorlar (dosya sistemi degisikligi yayinlar). }
procedure CurStepChanged(CurStep: TSetupStep);
var
  UninstallKey, UninstallCommand: string;
begin
  if CurStep = ssPostInstall then begin
    { Dosyalar kuruldu; hosts temizligi + gorev kaldirma burada yapilir. Istege bagli
      "KJ Des'i baslat" secenegine BAGLI DEGILDIR ve silent kurulumda da calisir. }
    DropFailsafeTaskAfterHostsCleanup();
    { /SILENT skips Inno's redundant startup MsgBox, /KJDESUI keeps our
      explicit same-form consent page. Genuine unattended calls retain data. }
    { KJ Des's OWN uninstall key only (never another product's entry). }
    UninstallKey := 'Software\Microsoft\Windows\CurrentVersion\Uninstall\{#MyAppGuid}_is1';
    if RegQueryStringValue(HKLM64, UninstallKey, 'UninstallString', UninstallCommand) then begin
      if Pos('/KJDESUI=1', UninstallCommand) = 0 then
        if not RegWriteStringValue(HKLM64, UninstallKey, 'UninstallString',
          UninstallCommand + ' /SILENT /KJDESUI=1 /NORESTART') then
          Log('KJ Des: tek ekranli kaldirma komutu kaydedilemedi');
    end;
    SHChangeNotify(SHCNE_ASSOCCHANGED, SHCNF_IDLIST, 0, 0);
  end;
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  Code: Integer;
begin
  if (CurUninstallStep = usPostUninstall) and (DeleteUserSettings or DeleteUserLog) then begin
    if not DeleteSelectedUserData(UninstallUserDataPath, DeleteUserSettings, DeleteUserLog) then begin
      Log('KJ Des: secilen ayarlar/log temizligi tamamlanamadi: ' + UninstallUserDataPath);
      if UserUninstallUI then
        MsgBox(CustomMessage('UserDataPartial') + #13#10 + UninstallUserDataPath, mbError, MB_OK);
    end else
      Log('KJ Des: secilen ayarlar/log temizligi tamamlandi.');
  end;
  if CurUninstallStep = usPostUninstall then CleanupUninstallCache();
  if CurUninstallStep = usUninstall then begin
    if not UninstallOptionsAccepted then Abort;
    { Recheck immediately before removal, including silent uninstall. }
    if ConnectionRequiresRestore() or not StopVerifiedPassiveKJDes() then
      RaiseException('KJ Des aktif veya guvenle kapatilamadi; kaldirma durduruldu.');
    { 2) hosts yonlendirmesini temizle }
    if not CleanHostsBlock(HostsFilePath()) then begin
      Log('KJ Des KALDIRMA: hosts yonlendirmesi temizlenemedi/dogrulanamadi');
      if not UninstallSilent then
        MsgBox(CustomMessage('UninstallHostsFailed'), mbError, MB_OK);
    end;
    { 3) logon guvenlik gorevini sil. KALDIRMA yolunda bu KOSULSUZDUR: hedef exe
         birazdan silinecegi icin gorev zaten calisamaz; ayakta kalmasi yalnizca
         her oturum acilista basarisiz bir HIGHEST gorev birakirdi. }
    Exec(ExpandConstant('{cmd}'), '/C schtasks /Delete /TN "KJDesHostsFailsafe" /F',
         '', SW_HIDE, ewWaitUntilTerminated, Code);
  end;
end;
