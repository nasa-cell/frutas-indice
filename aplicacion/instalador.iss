; Instalador de Corte Frutal (diseño C: una sola pantalla con el fondo del juego).
; Se compila con aplicacion/compilar.sh

#define Version "1.0.0"
#ifndef Dist
  #define Dist "C:\herramientas\compilacion\corte-frutal\dist\Corte Frutal"
#endif

[Setup]
AppId={{9E0A8D99-BDE3-4DC0-A184-8581FD30402F}
AppName=Corte Frutal
AppVersion={#Version}
AppVerName=Corte Frutal {#Version}
AppPublisher=nasa-cell
DefaultDirName={autopf}\Corte Frutal
DefaultGroupName=Corte Frutal
DisableWelcomePage=no
DisableDirPage=yes
DisableProgramGroupPage=yes
DisableReadyPage=yes
DisableFinishedPage=no
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=commandline
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=..\pc instalador
OutputBaseFilename=Instalar Corte Frutal {#Version}
SetupIconFile=icono.ico
UninstallDisplayIcon={app}\Corte Frutal.exe
UninstallDisplayName=Corte Frutal
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
CloseApplications=yes

[Languages]
Name: "es"; MessagesFile: "compiler:Languages\Spanish.isl"

[Files]
Source: "{#Dist}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "imagenes\*.bmp"; Flags: dontcopy

[Icons]
Name: "{autodesktop}\Corte Frutal"; Filename: "{app}\Corte Frutal.exe"; Check: QuiereEscritorio
Name: "{autoprograms}\Corte Frutal"; Filename: "{app}\Corte Frutal.exe"; Check: QuiereInicio

[Code]
const
  COLOR_PANEL = $0030160B;   { #0b1630 en BGR }
  COLOR_DORADO = $0032B6F2;  { #f2b632 }
  COLOR_SUAVE = $00F5DED2;

var
  Capa: TPanel;
  Fondo, BotonPrincipal, BotonCerrar, Barra: TBitmapImage;
  Opciones: TPanel;
  Resumen, Cambiar, Porcentaje: TNewStaticText;
  TxtMi, TxtTodos, TxtEscritorio, TxtInicio, TxtCarpeta: TNewStaticText;
  RadioMi, RadioTodos: TNewRadioButton;
  ChkEscritorio, ChkInicio: TNewCheckBox;
  Ruta: TNewEdit;
  Examinar: TNewButton;
  RutaInicial: String;
  Saliendo, Abierto: Boolean;

function QuiereEscritorio: Boolean;
begin
  Result := ChkEscritorio.Checked;
end;

function QuiereInicio: Boolean;
begin
  Result := ChkInicio.Checked;
end;

procedure Cargar(Img: TBitmapImage; Nombre: String);
begin
  ExtractTemporaryFile(Nombre);
  Img.Bitmap.LoadFromFile(ExpandConstant('{tmp}\') + Nombre);
end;

function Imagen(Nombre: String; X, Y, W, H: Integer): TBitmapImage;
begin
  Result := TBitmapImage.Create(Capa);
  Result.Parent := Capa;
  Result.SetBounds(ScaleX(X), ScaleY(Y), ScaleX(W), ScaleY(H));
  Result.Stretch := True;
  Cargar(Result, Nombre);
end;

function Texto(Padre: TWinControl; Cad: String; X, Y, W: Integer; Color: TColor; Tam: Integer): TNewStaticText;
begin
  Result := TNewStaticText.Create(Padre);
  Result.Parent := Padre;
  Result.AutoSize := False;
  Result.WordWrap := True;
  Result.ParentColor := False;
  Result.Color := COLOR_PANEL;
  Result.Font.Name := 'Segoe UI';
  Result.Font.Size := Tam;
  Result.Font.Color := Color;
  Result.Caption := Cad;
  Result.SetBounds(ScaleX(X), ScaleY(Y), ScaleX(W), ScaleY(Tam * 2 + 4));
end;

procedure ActualizarResumen;
var
  Para, Iconos: String;
begin
  if RadioTodos.Checked then Para := 'todos los usuarios' else Para := 'solo para mí';
  if ChkEscritorio.Checked and ChkInicio.Checked then Iconos := 'escritorio e Inicio'
  else if ChkEscritorio.Checked then Iconos := 'escritorio'
  else if ChkInicio.Checked then Iconos := 'Inicio'
  else Iconos := 'ninguno';
  Resumen.Caption := 'Para:  ' + Para + #13#10 + 'Carpeta:  ' + Ruta.Text + #13#10 +
    'Íconos:  ' + Iconos + #13#10 + 'Espacio:  unos 330 MB';
end;

procedure MostrarOpciones(Si: Boolean);
begin
  Abierto := Si;
  ActualizarResumen;
  Resumen.Visible := not Si;
  Opciones.Visible := Si;
  if Si then Cambiar.Caption := 'Listo, ocultar opciones' else Cambiar.Caption := 'Cambiar';
end;

procedure ClicCambiar(Sender: TObject);
begin
  MostrarOpciones(not Abierto);
end;

procedure ClicTexto(Sender: TObject);
begin
  if Sender = TxtMi then RadioMi.Checked := True
  else if Sender = TxtTodos then RadioTodos.Checked := True
  else if Sender = TxtEscritorio then ChkEscritorio.Checked := not ChkEscritorio.Checked
  else if Sender = TxtInicio then ChkInicio.Checked := not ChkInicio.Checked;
  ActualizarResumen;
end;

procedure ClicOpcion(Sender: TObject);
begin
  ActualizarResumen;
end;

procedure ClicExaminar(Sender: TObject);
var
  Dir: String;
begin
  Dir := Ruta.Text;
  if BrowseForFolder('Elige dónde instalar Corte Frutal:', Dir, True) then
  begin
    if CompareText(ExtractFileName(RemoveBackslashUnlessRoot(Dir)), 'Corte Frutal') <> 0 then
      Dir := AddBackslash(Dir) + 'Corte Frutal';
    Ruta.Text := Dir;
    ActualizarResumen;
  end;
end;

function SiNo(B: Boolean): String;
begin
  if B then Result := '1' else Result := '0';
end;

procedure Siguiente;
begin
  WizardForm.NextButton.OnClick(WizardForm.NextButton);
end;

procedure ClicInstalar(Sender: TObject);
var
  Params: String;
  Err: Integer;
begin
  if Trim(Ruta.Text) = '' then
  begin
    MsgBox('Escribe la carpeta donde se instala el juego.', mbError, MB_OK);
    Exit;
  end;
  if RadioTodos.Checked and not IsAdminInstallMode then
  begin
    { Para todos los usuarios hace falta permiso de administrador: se abre de nuevo pidiéndolo }
    Params := '/ALLUSERS /AUTO=1 /ESCRITORIO=' + SiNo(ChkEscritorio.Checked) + ' /INICIO=' + SiNo(ChkInicio.Checked);
    if CompareText(Ruta.Text, RutaInicial) <> 0 then
      Params := Params + ' /DIR="' + Ruta.Text + '"';
    if ShellExec('open', ExpandConstant('{srcexe}'), Params, '', SW_SHOW, ewNoWait, Err) then
    begin
      Saliendo := True;
      WizardForm.Close;
    end else
      MsgBox('No se pudo pedir permiso de administrador.', mbError, MB_OK);
    Exit;
  end;
  WizardForm.DirEdit.Text := Ruta.Text;
  Siguiente;
end;

procedure ClicJugar(Sender: TObject);
var
  Err: Integer;
begin
  ExecAsOriginalUser(ExpandConstant('{app}\Corte Frutal.exe'), '', ExpandConstant('{app}'), SW_SHOWNORMAL, ewNoWait, Err);
  Siguiente;
end;

procedure ClicCerrar(Sender: TObject);
begin
  Siguiente;
end;

procedure InitializeWizard;
var
  Y: Integer;
begin
  WizardForm.Caption := 'Instalar Corte Frutal {#Version}';
  WizardForm.ClientWidth := ScaleX(520);
  WizardForm.ClientHeight := ScaleY(600);
  WizardForm.Position := poScreenCenter;

  Capa := TPanel.Create(WizardForm);
  Capa.Parent := WizardForm;
  Capa.BevelOuter := bvNone;
  Capa.SetBounds(0, 0, WizardForm.ClientWidth, WizardForm.ClientHeight);
  Capa.BringToFront;

  Fondo := Imagen('inicio.bmp', 0, 0, 520, 600);
  BotonPrincipal := Imagen('inicio_boton.bmp', 150, 486, 220, 54);
  BotonPrincipal.Cursor := crHand;
  BotonPrincipal.OnClick := @ClicInstalar;
  BotonCerrar := Imagen('listo_cerrar.bmp', 200, 552, 120, 32);
  BotonCerrar.Cursor := crHand;
  BotonCerrar.OnClick := @ClicCerrar;
  BotonCerrar.Visible := False;
  Barra := Imagen('barra.bmp', 40, 300, 0, 24);
  Barra.Visible := False;

  RutaInicial := WizardForm.DirEdit.Text;
  Ruta := TNewEdit.Create(Capa);   { se ubica más abajo dentro de Opciones }

  Resumen := Texto(Capa, '', 44, 214, 432, clWhite, 10);
  Resumen.Height := ScaleY(110);

  Opciones := TPanel.Create(Capa);
  Opciones.Parent := Capa;
  Opciones.BevelOuter := bvNone;
  Opciones.ParentBackground := False;
  Opciones.Color := COLOR_PANEL;
  Opciones.SetBounds(ScaleX(40), ScaleY(210), ScaleX(440), ScaleY(214));

  Y := 4;
  RadioMi := TNewRadioButton.Create(Opciones);
  RadioMi.Parent := Opciones;
  RadioMi.SetBounds(ScaleX(4), ScaleY(Y + 2), ScaleX(16), ScaleY(18));
  RadioMi.Checked := not IsAdminInstallMode;
  RadioMi.OnClick := @ClicOpcion;
  TxtMi := Texto(Opciones, 'Solo para mí (no pide permiso de administrador)', 26, Y, 400, clWhite, 10);
  TxtMi.Cursor := crHand;
  TxtMi.OnClick := @ClicTexto;

  Y := Y + 28;
  RadioTodos := TNewRadioButton.Create(Opciones);
  RadioTodos.Parent := Opciones;
  RadioTodos.SetBounds(ScaleX(4), ScaleY(Y + 2), ScaleX(16), ScaleY(18));
  RadioTodos.Checked := IsAdminInstallMode;
  RadioTodos.OnClick := @ClicOpcion;
  TxtTodos := Texto(Opciones, 'Para todos los usuarios (pide permiso)', 26, Y, 400, clWhite, 10);
  TxtTodos.Cursor := crHand;
  TxtTodos.OnClick := @ClicTexto;

  Y := Y + 34;
  TxtCarpeta := Texto(Opciones, 'Carpeta (puedes cambiar el disco):', 4, Y, 420, COLOR_SUAVE, 9);
  Y := Y + 22;
  Ruta.Parent := Opciones;
  Ruta.SetBounds(ScaleX(4), ScaleY(Y), ScaleX(324), ScaleY(25));
  Ruta.Text := RutaInicial;
  Examinar := TNewButton.Create(Opciones);
  Examinar.Parent := Opciones;
  Examinar.Caption := 'Examinar...';
  Examinar.SetBounds(ScaleX(336), ScaleY(Y - 1), ScaleX(100), ScaleY(27));
  Examinar.OnClick := @ClicExaminar;

  Y := Y + 40;
  ChkEscritorio := TNewCheckBox.Create(Opciones);
  ChkEscritorio.Parent := Opciones;
  ChkEscritorio.SetBounds(ScaleX(4), ScaleY(Y + 2), ScaleX(16), ScaleY(18));
  ChkEscritorio.Checked := ExpandConstant('{param:ESCRITORIO|1}') = '1';
  ChkEscritorio.OnClick := @ClicOpcion;
  TxtEscritorio := Texto(Opciones, 'Ícono en el escritorio', 26, Y, 400, clWhite, 10);
  TxtEscritorio.Cursor := crHand;
  TxtEscritorio.OnClick := @ClicTexto;

  Y := Y + 28;
  ChkInicio := TNewCheckBox.Create(Opciones);
  ChkInicio.Parent := Opciones;
  ChkInicio.SetBounds(ScaleX(4), ScaleY(Y + 2), ScaleX(16), ScaleY(18));
  ChkInicio.Checked := ExpandConstant('{param:INICIO|1}') = '1';
  ChkInicio.OnClick := @ClicOpcion;
  TxtInicio := Texto(Opciones, 'Ícono en el menú Inicio', 26, Y, 400, clWhite, 10);
  TxtInicio.Cursor := crHand;
  TxtInicio.OnClick := @ClicTexto;

  Cambiar := Texto(Capa, 'Cambiar', 44, 434, 300, COLOR_DORADO, 10);
  Cambiar.Font.Style := [fsUnderline];
  Cambiar.Cursor := crHand;
  Cambiar.OnClick := @ClicCambiar;

  Porcentaje := Texto(Capa, '', 40, 336, 440, clWhite, 11);
  Porcentaje.Visible := False;
  Porcentaje.AutoSize := True;
  Porcentaje.WordWrap := False;

  MostrarOpciones(False);
end;

function ShouldSkipPage(PageID: Integer): Boolean;
begin
  { Si se abrió de nuevo para todos los usuarios, va directo a instalar }
  Result := (PageID = wpWelcome) and (ExpandConstant('{param:AUTO|0}') = '1');
end;

procedure PantallaInstalando;
begin
  Cargar(Fondo, 'instalando.bmp');
  BotonPrincipal.Visible := False;
  Resumen.Visible := False;
  Opciones.Visible := False;
  Cambiar.Visible := False;
  Barra.Visible := True;
  Porcentaje.Visible := True;
  Porcentaje.Color := $00672E18;
  Porcentaje.Caption := '0 %';
end;

procedure CurPageChanged(CurPageID: Integer);
begin
  if CurPageID = wpWelcome then
    Capa.Visible := True
  else if CurPageID = wpInstalling then
  begin
    Capa.Visible := True;
    PantallaInstalando;
  end
  else if CurPageID = wpFinished then
  begin
    Capa.Visible := True;
    Cargar(Fondo, 'listo.bmp');
    Barra.Visible := False;
    Porcentaje.Visible := False;
    Cargar(BotonPrincipal, 'listo_jugar.bmp');
    BotonPrincipal.OnClick := @ClicJugar;
    BotonPrincipal.Visible := True;
    BotonCerrar.Visible := True;
  end
  else
    Capa.Visible := False;   { cualquier otra pantalla (por ejemplo, cerrar el juego abierto) se ve normal }
end;

procedure CurInstallProgressChanged(CurProgress, MaxProgress: Integer);
begin
  if MaxProgress <= 0 then Exit;
  Barra.Width := ScaleX(440) * CurProgress div MaxProgress;
  Porcentaje.Caption := IntToStr(CurProgress * 100 div MaxProgress) + ' %';
  Porcentaje.Left := (Capa.Width - Porcentaje.Width) div 2;
end;

procedure CancelButtonClick(CurPageID: Integer; var Cancel, Confirm: Boolean);
begin
  if Saliendo then Confirm := False;
end;
