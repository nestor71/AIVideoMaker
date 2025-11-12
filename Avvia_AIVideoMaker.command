#!/bin/bash

# ========================================
# AIVideoMaker - Launcher per macOS
# ========================================
# Script per avviare automaticamente l'applicazione AIVideoMaker
# Doppio clic su questo file per avviare l'applicazione

# Colori per output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Banner
echo ""
echo "╔════════════════════════════════════════════╗"
echo "║     AIVideoMaker Professional Launcher     ║"
echo "╚════════════════════════════════════════════╝"
echo ""

# Ottieni la directory dello script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

echo -e "${BLUE}📁 Directory progetto:${NC} $SCRIPT_DIR"
echo ""

# ========================================
# 1. CONTROLLA E ATTIVA VIRTUAL ENVIRONMENT
# ========================================

VENV_DIR="$SCRIPT_DIR/venv"

if [ ! -d "$VENV_DIR" ]; then
    echo -e "${YELLOW}⚠️  Virtual environment non trovato${NC}"
    echo -e "${BLUE}📦 Creazione virtual environment...${NC}"

    python3 -m venv venv

    if [ $? -ne 0 ]; then
        echo -e "${RED}❌ Errore nella creazione del virtual environment${NC}"
        echo ""
        echo "Assicurati di avere Python 3.8+ installato:"
        echo "  brew install python3"
        echo ""
        read -p "Premi INVIO per chiudere..."
        exit 1
    fi

    echo -e "${GREEN}✅ Virtual environment creato${NC}"
    echo ""
fi

# Attiva virtual environment
echo -e "${BLUE}🔄 Attivazione virtual environment...${NC}"
source "$VENV_DIR/bin/activate"

if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Errore nell'attivazione del virtual environment${NC}"
    read -p "Premi INVIO per chiudere..."
    exit 1
fi

echo -e "${GREEN}✅ Virtual environment attivato${NC}"
echo ""

# ========================================
# 2. INSTALLA/AGGIORNA DIPENDENZE
# ========================================

if [ ! -f "$VENV_DIR/.dependencies_installed" ]; then
    echo -e "${BLUE}📦 Installazione dipendenze...${NC}"
    echo -e "${YELLOW}   (Questo potrebbe richiedere qualche minuto alla prima esecuzione)${NC}"
    echo ""

    pip install --upgrade pip
    pip install -r requirements.txt

    if [ $? -ne 0 ]; then
        echo -e "${RED}❌ Errore nell'installazione delle dipendenze${NC}"
        echo ""
        echo "Prova a installare manualmente:"
        echo "  source venv/bin/activate"
        echo "  pip install -r requirements.txt"
        echo ""
        read -p "Premi INVIO per chiudere..."
        exit 1
    fi

    # Crea marker file per indicare che le dipendenze sono installate
    touch "$VENV_DIR/.dependencies_installed"

    echo ""
    echo -e "${GREEN}✅ Dipendenze installate${NC}"
    echo ""
fi

# ========================================
# 3. CONTROLLA FILE .env
# ========================================

if [ ! -f ".env" ]; then
    echo -e "${YELLOW}⚠️  File .env non trovato${NC}"

    if [ -f ".env.example" ]; then
        echo -e "${BLUE}📋 Creazione .env da .env.example...${NC}"
        cp .env.example .env
        echo -e "${GREEN}✅ File .env creato${NC}"
        echo -e "${YELLOW}⚠️  IMPORTANTE: Configura le chiavi API nel file .env${NC}"
        echo ""
    else
        echo -e "${RED}❌ Nessun template .env.example trovato${NC}"
    fi
fi

# ========================================
# 4. AVVIA SERVER
# ========================================

echo -e "${BLUE}🚀 Avvio server AIVideoMaker...${NC}"
echo ""

# Controlla se la porta 8000 è già in uso
if lsof -Pi :8000 -sTCP:LISTEN -t >/dev/null 2>&1 ; then
    echo -e "${YELLOW}⚠️  Porta 8000 già in uso${NC}"
    echo ""
    echo "Vuoi terminare il processo esistente e riavviare? (s/n)"
    read -r response

    if [[ "$response" =~ ^[Ss]$ ]]; then
        echo -e "${BLUE}🔄 Terminazione processo su porta 8000...${NC}"
        lsof -ti:8000 | xargs kill -9 2>/dev/null
        sleep 2
    else
        echo -e "${BLUE}📱 Apertura browser...${NC}"
        sleep 2
        open "http://localhost:8000"
        exit 0
    fi
fi

# Avvia il server in background
python main.py > /tmp/aividemaker.log 2>&1 &
SERVER_PID=$!

echo -e "${GREEN}✅ Server avviato (PID: $SERVER_PID)${NC}"
echo ""

# ========================================
# 5. ATTENDI CHE IL SERVER SIA PRONTO
# ========================================

echo -e "${BLUE}⏳ Attendo che il server sia pronto...${NC}"

MAX_ATTEMPTS=30
ATTEMPT=0

while [ $ATTEMPT -lt $MAX_ATTEMPTS ]; do
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Server pronto!${NC}"
        echo ""
        break
    fi

    # Controlla se il processo è ancora in esecuzione
    if ! ps -p $SERVER_PID > /dev/null 2>&1; then
        echo -e "${RED}❌ Il server si è interrotto inaspettatamente${NC}"
        echo ""
        echo "Log degli ultimi errori:"
        tail -n 20 /tmp/aividemaker.log
        echo ""
        read -p "Premi INVIO per chiudere..."
        exit 1
    fi

    ATTEMPT=$((ATTEMPT + 1))
    echo -n "."
    sleep 1
done

if [ $ATTEMPT -eq $MAX_ATTEMPTS ]; then
    echo ""
    echo -e "${RED}❌ Timeout: il server non risponde${NC}"
    echo ""
    echo "Log degli ultimi errori:"
    tail -n 20 /tmp/aividemaker.log
    echo ""
    read -p "Premi INVIO per chiudere..."
    kill $SERVER_PID 2>/dev/null
    exit 1
fi

# ========================================
# 6. APRI/RICARICA BROWSER
# ========================================

echo -e "${BLUE}🌐 Apertura browser...${NC}"
sleep 1

APP_URL="http://localhost:8000"

# Funzione per aprire/ricaricare in Safari
open_or_reload_safari() {
    osascript <<EOF 2>/dev/null
tell application "Safari"
    set targetURL to "$APP_URL"
    set tabFound to false

    -- Cerca una scheda esistente con l'URL
    repeat with w in windows
        repeat with t in tabs of w
            if URL of t contains "localhost:8000" then
                set tabFound to true
                -- Porta la finestra in primo piano
                set index of w to 1
                -- Seleziona la scheda
                set current tab of w to t
                -- Ricarica la pagina
                tell t to do JavaScript "window.location.reload()"
                activate
                exit repeat
            end if
        end repeat
        if tabFound then exit repeat
    end repeat

    -- Se non trovata, apri nuova scheda/finestra
    if not tabFound then
        if (count of windows) > 0 then
            tell front window
                set current tab to (make new tab with properties {URL:targetURL})
            end tell
        else
            make new document with properties {URL:targetURL}
        end if
        activate
    end if
end tell
EOF
    return $?
}

# Funzione per aprire/ricaricare in Chrome
open_or_reload_chrome() {
    osascript <<EOF 2>/dev/null
tell application "Google Chrome"
    set targetURL to "$APP_URL"
    set tabFound to false

    -- Cerca una scheda esistente con l'URL
    repeat with w in windows
        repeat with t in tabs of w
            if URL of t contains "localhost:8000" then
                set tabFound to true
                -- Porta la finestra in primo piano
                set index of w to 1
                -- Seleziona e ricarica la scheda
                set active tab index of w to (index of t)
                tell t to reload
                activate
                exit repeat
            end if
        end repeat
        if tabFound then exit repeat
    end repeat

    -- Se non trovata, apri nuova scheda/finestra
    if not tabFound then
        if (count of windows) > 0 then
            tell front window
                make new tab with properties {URL:targetURL}
            end tell
        else
            make new window with properties {URL:targetURL}
        end if
        activate
    end if
end tell
EOF
    return $?
}

# Rileva e usa il browser predefinito
DEFAULT_BROWSER=$(defaults read ~/Library/Preferences/com.apple.LaunchServices/com.apple.launchservices.secure LSHandlers 2>/dev/null | grep -B 1 'LSHandlerURLScheme.*http' | grep 'LSHandlerRoleAll' | head -1 | sed -E 's/.*"(.*)".*/\1/' || echo "")

BROWSER_OPENED=false

# Prova prima con il browser predefinito
if [[ "$DEFAULT_BROWSER" == *"safari"* ]] || [[ "$DEFAULT_BROWSER" == *"Safari"* ]]; then
    echo -e "${BLUE}   Uso Safari (browser predefinito)${NC}"
    if open_or_reload_safari; then
        BROWSER_OPENED=true
    fi
elif [[ "$DEFAULT_BROWSER" == *"chrome"* ]] || [[ "$DEFAULT_BROWSER" == *"Chrome"* ]]; then
    echo -e "${BLUE}   Uso Chrome (browser predefinito)${NC}"
    if open_or_reload_chrome; then
        BROWSER_OPENED=true
    fi
fi

# Se non ha funzionato, prova Safari
if [ "$BROWSER_OPENED" = false ]; then
    if pgrep -x "Safari" > /dev/null 2>&1 || [ -d "/Applications/Safari.app" ]; then
        echo -e "${BLUE}   Tentativo con Safari...${NC}"
        if open_or_reload_safari; then
            BROWSER_OPENED=true
        fi
    fi
fi

# Se Safari non ha funzionato, prova Chrome
if [ "$BROWSER_OPENED" = false ]; then
    if pgrep -x "Google Chrome" > /dev/null 2>&1 || [ -d "/Applications/Google Chrome.app" ]; then
        echo -e "${BLUE}   Tentativo con Chrome...${NC}"
        if open_or_reload_chrome; then
            BROWSER_OPENED=true
        fi
    fi
fi

# Fallback: usa il comando open standard
if [ "$BROWSER_OPENED" = false ]; then
    echo -e "${BLUE}   Uso browser di sistema...${NC}"
    open "$APP_URL"
fi

echo ""
echo "╔════════════════════════════════════════════╗"
echo "║         AIVideoMaker è in esecuzione!      ║"
echo "╚════════════════════════════════════════════╝"
echo ""
echo -e "${GREEN}✅ Applicazione disponibile su:${NC} http://localhost:8000"
echo ""
echo -e "${YELLOW}📌 Istruzioni:${NC}"
echo "   • Il browser si è aperto automaticamente"
echo "   • Il server continua a girare in background"
echo "   • Per fermare il server: killall python"
echo "   • Per vedere i log: tail -f /tmp/aividemaker.log"
echo ""
echo -e "${BLUE}═══════════════════════════════════════════${NC}"
echo ""

# Mantieni il terminale aperto (opzionale)
echo -e "${YELLOW}Puoi chiudere questa finestra - il server continuerà a girare${NC}"
echo -e "${YELLOW}oppure premi CTRL+C per fermarlo${NC}"
echo ""

# Aspetta che l'utente prema CTRL+C
trap "echo ''; echo -e '${BLUE}🛑 Arresto server...${NC}'; kill $SERVER_PID 2>/dev/null; echo -e '${GREEN}✅ Server fermato${NC}'; exit 0" INT TERM

# Tieni traccia del processo server
wait $SERVER_PID
