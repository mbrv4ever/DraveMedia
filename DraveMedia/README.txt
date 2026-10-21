DraveMedia v0.28
===============
Alles-in-een mediaspeler (Dravenlock).

Onderdelen:
- Speler: speelt media af. Open losse bestanden of een hele map (afspeellijst).
  Knoppen: vorige/afspelen/stop/volgende, tijdbalk, volume/dempen, volledig scherm.
  Spatiebalk = afspelen/pauze. Slepen-en-neerzetten werkt ook.
  Volledig scherm: dubbelklik op het beeld of de knop; Escape om terug.
  Backend-keuze: 'Systeem (Qt)' werkt meteen met de codecs van Windows.
  'VLC (alle formaten)' gebruikt VLC voor zo goed als elk formaat - vereist dat
  VLC op de pc staat (anders valt de app netjes terug op Qt).
- Afbeeldingen: opent alle gangbare beeldformaten. Zoom, passend maken, draaien,
  vorige/volgende door een map. Slepen-en-neerzetten werkt ook.
- Server: kies een map en klik Starten. De serverpagina is een DOORLOPENDE
  speler (als een online radio): open http://JOUW-IP:poort in een browser en
  speel alle muziek/video automatisch achter elkaar af. Media wordt automatisch
  gecategoriseerd in Muziek / Video / Afbeeldingen (zoals Plex-bibliotheken),
  ongeacht in welke submap het staat. Knoppen: 'Speel alles', 'Herhaal alles',
  'Shuffle'. De speler heeft alleen de basis-URL nodig. Andere apparaten in je netwerk kunnen dan
  naar de getoonde URL (http://JOUW-IP:poort/) en je media streamen/downloaden.
  Ondersteunt 'Range' (vooruit/terug spoelen in video werkt). Klik op een bestand in de lijst (links) om het rechts in de pagina af te
  spelen. Dubbelklik een URL
  om 'm te openen, of kopieer de link.
- De spelers (server-pagina en gegenereerde HTML5) gebruiken de strakke
  Plyr-speler (via internet ingeladen; zonder internet val je terug op de
  standaard browserspeler).
- HTML5: genereert een kant-en-klare HTML5-speler voor op een website. Klik je
  op 'Genereer', dan verschijnt rechts naast de code meteen een LIVE voorbeeld
  in de ingebouwde browser. (Werkt run.bat de eerste keer? Dan installeert hij
  de ingebouwde browser automatisch; bestond je .venv al, dan vult run.bat dat
  nu vanzelf aan.) Kies bovenin de modus
  'Hele server (doorlopende speler)' om een pagina te maken die alleen de
  server-URL nodig heeft en de hele bibliotheek doorlopend afspeelt. Of genereer
  een speler voor een enkel bestand/URL.
  Met 'Bekijk in browser' open je het resultaat meteen: in servermodus
  opent je server-URL (de live speler), bij een enkel bestand een
  voorbeeldpagina. Als PyQt6-WebEngine aanwezig is (wordt door run.bat
  geinstalleerd) opent dit in een INGEBOUWDE browser; anders je systeembrowser. Gegenereerde pagina's mogen door de CORS-instelling ook
  vanaf een andere website de stream ophalen.
  Kies een bestand of typ een URL, stel titel/poster/opties in, en sla op.
  Met 'mediabestand ernaast kopiëren' zet hij het bestand naast de .html.
  Tip: vul 'Server-URL' in (knop 'van server' als de server draait) en kies
  dan een bestand bij 'Bestand op server' - de volledige stream-URL wordt
  automatisch ingevuld. Zo maak je een speler die rechtstreeks van de
  streaming-server speelt, zonder lokaal bestand. Afbeeldingen (ook .webp)
  worden als <img> gezet.

STARTEN (zonder te bouwen):
- Dubbelklik run.bat. De eerste keer installeert hij eenmalig wat nodig is
  (Python 3.10-3.13 vereist). Werkt iets niet meer? Draai herstel.bat.

PORTABLE .EXE MAKEN:
- Dubbelklik bouw-exe.bat. Resultaat: dist\DraveMedia.exe (een enkel bestand).
- Eigen icoon? Zet een afbeelding 'icon.png' (vierkant, bijv. 256x256) in deze map
  voor het bouwen; die wordt automatisch omgezet en meegebakken.

Contact: service@dravenlock.nl


.EXE bouwen (v0.11)
-------------------
De build is 'onefolder' vanwege de ingebouwde browser (QtWebEngine), net als
DraveMaster. Resultaat: map dist\DraveMedia\ met DraveMedia.exe + _internal.
Houd die samen; maak voor het bureaublad een snelkoppeling naar de .exe.


Ingebouwde browser (v0.13)
--------------------------
De ingebouwde browser (QtWebEngine) wordt nu correct geladen (net als in
DraveMaster). run.bat bouwt de omgeving automatisch opnieuw op als de
ingebouwde browser ontbreekt. Werkt het toch niet vanuit run.bat? Bouw dan
de .exe met bouw-exe.bat - daar zit de browser sowieso in meegebakken.


Serverpagina als app (PWA) (v0.14)
----------------------------------
De serverpagina is nu een volledige PWA: open http://<jouw-ip>:<poort>/ op je
telefoon of pc en kies 'Toevoegen aan beginscherm' / 'Installeren'. De app
opent dan in een eigen venster en de schil werkt ook offline (media blijft
streamen vanaf de server, dus die heeft de server wel nodig). Nieuw: knop
'Code kopieren' op het HTML5-tabblad kopieert de broncode naar het klembord.


Website (PWA) exporteren (v0.16)
--------------------------------
Op het Server-tabblad: vul je Server-map in, en (optioneel) een 'Media-URL' waar
de media op je server staat. Leeg = de media staat naast de speler. Klik
'Website (PWA) exporteren...' -> DraveMedia maakt ALLEEN de PWA-bestanden:
index.html, media.json, manifest.webmanifest, sw.js en dm-icon.svg. De media wordt
NIET gekopieerd; die blijft op de server staan en wordt gestreamd. Upload de map
naar je BEVEILIGDE site (HTTPS), bijv. https://jouw-domein/mediaspeler/. Daar werkt
installeren op het beginscherm en offline.

De Snelgids en de donatieknop zitten IN de app zelf (knop 'Snelgids' in de kop en
'Donatie' rechtsonder in de statusbalk).


Hosten op HTTPS (Apache) (v0.17)
--------------------------------
De in-app Snelgids ('Snelgids'-knop) bevat nu een stap-voor-stap hoofdstuk om de
speler op een beveiligde site (HTTPS) te zetten met Apache: een Alias /media naar
je mediamap (op welke schijf dan ook; niets wordt gekopieerd), Media-URL = /media/
in de export, en de PWA-bestanden in bijv. /htdocs/jouwsite/mediaspeler/. Daarna
speelt en installeert het via https://jouw-domein/mediaspeler/.


Uitgebreide snelgids (v0.18)
----------------------------
De in-app Snelgids ('Snelgids'-knop) is nu een volledige handleiding (NL + EN) met
drie routes van makkelijk naar geavanceerd: 1) gewoon thuis afspelen via de
ingebouwde server, 2) installeren op het beginscherm via HTTPS (eigen webserver met
Apache-Alias, of gratis tunnel zoals Cloudflare/Tailscale), 3) HTML5-code voor je
eigen website. Plus een hoofdstuk probleemoplossing (404, Forbidden, cache/Ctrl+F5,
mixed content, wifi/firewall, installeer-popup).


Live lijst via PHP (v0.19)
--------------------------
Op het Server-tabblad kun je 'Live lijst via PHP' aanvinken. De export maakt dan een
media.php die je mediamap LIVE scant (zelfde JSON als media.json). Nieuwe media
verschijnt meteen, zonder opnieuw te exporteren. Vereist een server met PHP (XAMPP
heeft dat standaard). index.html leest dan media.php i.p.v. media.json.


Speelt elk formaat af (v0.20)
-----------------------------
DraveMedia kiest nu automatisch hoe een video het best speelt: web-vriendelijke
bestanden direct (snel), juiste codec maar verkeerde verpakking = razendsnel
herverpakken (remux), en de rest wordt omgezet (transcode) naar HLS zodat het
overal speelt - ook .mkv/.avi/HEVC, ook op de telefoon. Hiervoor moeten ffmpeg en
ffprobe naast DraveMedia staan (of in je PATH). Ontbreken ze, dan speelt alleen wat
de browser zelf aankan (zoals voorheen). De ingebouwde speler gebruikt hls.js.


FFmpeg automatisch (v0.21)
--------------------------
Heb je FFmpeg nog niet, dan downloadt DraveMedia bij de eerste start AUTOMATISCH
ffmpeg.exe en ffprobe.exe (~80 MB) en zet ze naast de app (submap 'ffmpeg') - met een
voortgangsbalk. Geen vraag, want FFmpeg is nodig voor alle formaten. Je kunt ze ook zelf
daar of in je PATH zetten. Lukt de download niet (geen internet/firewall), dan zegt de app
dat en speelt voorlopig alleen wat de browser zelf aankan.


Zuiniger met geheugen (v0.23)
-----------------------------
De ingebouwde browser (Chromium) voor het 'Live voorbeeld' wordt nu pas geladen
zodra je het HTML5-tabblad echt opent - niet meer bij het opstarten. Gebruik je
alleen Speler en Server, dan blijft DraveMedia veel zuiniger met geheugen.


Toegangscode (v0.24)
--------------------
Maak je de server via internet bereikbaar (poort doorsturen op je router), zet dan
op het Server-tabblad een Toegangscode. De browser vraagt die eenmalig en onthoudt
'm; daarna is alles beschermd: speler, lijst en de streams. Leeg = open (alleen veilig
op je eigen wifi). Let op: via http is de code onderweg niet versleuteld; voor echt
waterdicht is later https/eigen domein nodig.


HTTPS (v0.25)
-------------
Wil je de app installeren als PWA, dan is HTTPS nodig. Op het Server-tabblad kun je
'HTTPS gebruiken' aanzetten en je Let's Encrypt-bestanden (fullchain.pem + privkey.pem)
aanwijzen, plus je domein. Open dan https://JOUW-DOMEIN:poort/. Heb je nog geen
certificaat, laat HTTPS dan uit en gebruik http (op Android kun je een snelkoppeling
naar het beginscherm maken).


Via je beveiligde site (v0.26)
------------------------------
Je kunt de DraveMedia-server achter je bestaande HTTPS-site hangen (reverse proxy),
zodat de mobiel installeerbaar is EN alle formaten spelen, zonder nieuw certificaat:
1) Zet in Apache de modules proxy_module en proxy_http_module aan.
2) In de https-vhost van je site:
     ProxyPreserveHost On
     ProxyPass        /dm/  http://127.0.0.1:8000/
     ProxyPassReverse /dm/  http://127.0.0.1:8000/
3) Start de DraveMedia-server op poort 8000 (HTTPS hoeft niet; Apache praat lokaal).
4) Open https://JOUW-SITE/dm/  -> installeerbaar, transcodeert, met toegangscode.
De speler past zich automatisch aan de submap /dm/ aan.


Installeerbaar icoon (v0.27)
----------------------------
Voor 'installeren als app' op Android maakt DraveMedia nu PNG-iconen (192 en 512 px).
Tip: als je telefoon alleen 'snelkoppeling' aanbood, sluit het tabblad volledig,
open https://JOUW-SITE/dm/ opnieuw, en kijk in het menu (drie puntjes) naar
'App installeren'.


Installatie-fix (v0.28)
-----------------------
De service worker is verbeterd: hij werkt onder een submap (/dm/), cachet het manifest en
de iconen niet meer (zodat updates meteen meetellen) en ruimt oude cache op. Bood je
telefoon eerder alleen een 'snelkoppeling' aan? Wis dan eenmalig de site-gegevens in de
browser (zodat de oude service worker weg is) en open https://JOUW-SITE/dm/ opnieuw.
