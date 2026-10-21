# edeco Toolbox

Die Toolbox verbindet die edeco-Programme. Sie enthält sie nicht.

| Repository | Inhalt |
|---|---|
| [Nova-Legenden](https://github.com/Dobolino/Nova-Legenden) | Legende aus Trimble-Nova-Plänen |
| [BIM2STEIGER](https://github.com/Dobolino/BIM2STEIGER) | Steiger-Katalog und Ausschreibung, Ordner `Steiger2Bim` |
| edeco-ag-toolbox | Lesezeichen auf diese Programme und die Zuordnung Nova-Symbol → Steiger-Artikel |

Weitere Werkzeuge kommen später als Lesezeichen dazu, zum Beispiel ein Projektbrowser. Dafür wird kein Programm in dieses Repository kopiert.

## Start

Python 3.11 oder neuer. Unter Windows `Start_Toolbox.cmd` doppelklicken, sonst:

```console
python server.py --open
```

Die Toolbox läuft unter http://127.0.0.1:8770 und ist nur auf diesem Rechner erreichbar. NOVA-Legenden und BIM2STEIGER verwenden beide standardmässig Port 8765. Wer beide gleichzeitig öffnet, startet eines davon mit einem anderen Port und passt das Lesezeichen an.

## Windows-Setup

NOVA-Legenden wird bereits so ausgeliefert. Dieselbe Art Setup gibt es für die Toolbox: bei jedem Stand auf `main` baut GitHub eine Datei `edeco-Toolbox-Setup-<Version>.exe` und legt sie unter den Releases ab. Die Installation braucht keine Administratorrechte und legt ein Desktop-Symbol an.

In der installierten Version steht auf der Startseite **Nach Updates suchen**. Ein neueres Setup wird geladen, still installiert, und die Toolbox startet neu. Lesezeichen und Zuordnungen bleiben erhalten, weil sie unter `%LOCALAPPDATA%\edeco-toolbox` liegen und nicht im Programmordner.

Solange man aus dem Quellcode startet, zeigt die Suche nur an, dass ein Update die installierte Windows-Version betrifft.

## Zuordnung

Unter «Zuordnung» zwei lokale Pfade eintragen:

- der Nova-Datensatz, zum Beispiel `Elektroinstallationen.V2.CH.nzp`
- der Steiger-Katalog `catalogue.sqlite` aus `Steiger2Bim/data`

Die Dateien bleiben an ihrem Ort. Eine Schablone ist die Palette, in der man das Symbol findet. Gespeichert wird die Zuordnung pro Funktion und Montageart: «Schalter, Schema 0» UP und AP bekommen getrennte Steiger-Artikel. Die Textvariante «(Ohne Text)» hängt an derselben Zuordnung wie das Symbol mit Text.

Eine Zuordnung speichert Artikelnummer, Verlegeart, Katalogjahr und auf Wunsch Einheit und BKP. Fehlende Einheiten bleiben leer.

Lesezeichen, Pfade und Zuordnungen liegen in `daten/` und werden nicht ins Git übernommen.

## Prüfen

```console
python -m unittest discover -s tests
```
