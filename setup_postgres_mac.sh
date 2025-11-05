#!/bin/bash
# ============================================
# Setup PostgreSQL per AIVideoMaker su macOS
# ============================================

set -e  # Exit on error

echo "🐘 Setup PostgreSQL per AIVideoMaker Professional"
echo "=================================================="
echo ""

# Colori per output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 1. Verifica Homebrew
echo "📦 Verifica Homebrew..."
if ! command -v brew &> /dev/null; then
    echo -e "${YELLOW}Homebrew non trovato. Installazione...${NC}"
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    echo ""
else
    echo -e "${GREEN}✓ Homebrew installato${NC}"
fi

# 2. Verifica PostgreSQL
echo ""
echo "🐘 Verifica PostgreSQL..."
if brew list postgresql@15 &> /dev/null; then
    echo -e "${GREEN}✓ PostgreSQL 15 già installato${NC}"
else
    echo -e "${YELLOW}PostgreSQL non trovato. Installazione...${NC}"
    brew install postgresql@15

    # Aggiungi al PATH
    if [[ "$SHELL" == *"zsh"* ]]; then
        echo 'export PATH="/opt/homebrew/opt/postgresql@15/bin:$PATH"' >> ~/.zshrc
        source ~/.zshrc
    elif [[ "$SHELL" == *"bash"* ]]; then
        echo 'export PATH="/opt/homebrew/opt/postgresql@15/bin:$PATH"' >> ~/.bash_profile
        source ~/.bash_profile
    fi

    echo -e "${GREEN}✓ PostgreSQL 15 installato${NC}"
fi

# 3. Avvia PostgreSQL
echo ""
echo "🚀 Avvio PostgreSQL..."
brew services start postgresql@15
sleep 3  # Aspetta che il servizio parta

# Verifica status
if brew services list | grep -q "postgresql@15.*started"; then
    echo -e "${GREEN}✓ PostgreSQL running${NC}"
else
    echo -e "${RED}✗ Errore: PostgreSQL non è partito${NC}"
    echo "Prova manualmente: brew services start postgresql@15"
    exit 1
fi

# 4. Crea database e utente
echo ""
echo "🗄️  Creazione database e utente..."

# Crea database (se non esiste)
if psql postgres -tAc "SELECT 1 FROM pg_database WHERE datname='aivideomaker'" | grep -q 1; then
    echo -e "${YELLOW}Database 'aivideomaker' già esistente${NC}"
else
    psql postgres -c "CREATE DATABASE aivideomaker;"
    echo -e "${GREEN}✓ Database 'aivideomaker' creato${NC}"
fi

# Crea utente (se non esiste)
if psql postgres -tAc "SELECT 1 FROM pg_roles WHERE rolname='aivideomaker'" | grep -q 1; then
    echo -e "${YELLOW}Utente 'aivideomaker' già esistente${NC}"
else
    psql postgres -c "CREATE USER aivideomaker WITH PASSWORD 'password';"
    echo -e "${GREEN}✓ Utente 'aivideomaker' creato${NC}"
fi

# Dai permessi
psql postgres -c "GRANT ALL PRIVILEGES ON DATABASE aivideomaker TO aivideomaker;" 2>/dev/null || true
echo -e "${GREEN}✓ Permessi assegnati${NC}"

# 5. Test connessione
echo ""
echo "🧪 Test connessione..."
if PGPASSWORD=password psql -h localhost -U aivideomaker -d aivideomaker -c "SELECT version();" > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Connessione al database OK${NC}"
    PGPASSWORD=password psql -h localhost -U aivideomaker -d aivideomaker -c "SELECT version();"
else
    echo -e "${RED}✗ Errore nella connessione${NC}"
    exit 1
fi

# 6. Verifica .env
echo ""
echo "📝 Verifica file .env..."
if [ -f .env ]; then
    if grep -q "DATABASE_URL=postgresql://aivideomaker:password@localhost:5432/aivideomaker" .env; then
        echo -e "${GREEN}✓ .env già configurato correttamente${NC}"
    else
        echo -e "${YELLOW}Aggiornamento DATABASE_URL in .env...${NC}"
        # Backup .env
        cp .env .env.backup
        # Sostituisci DATABASE_URL
        sed -i '' 's|^DATABASE_URL=.*|DATABASE_URL=postgresql://aivideomaker:password@localhost:5432/aivideomaker|' .env
        echo -e "${GREEN}✓ .env aggiornato (backup salvato in .env.backup)${NC}"
    fi
else
    echo -e "${RED}✗ File .env non trovato!${NC}"
    echo "Crea .env da .env.example e riprova"
    exit 1
fi

echo ""
echo "=================================================="
echo -e "${GREEN}✅ Setup PostgreSQL completato con successo!${NC}"
echo "=================================================="
echo ""
echo "🚀 Ora puoi avviare l'applicazione:"
echo "   python3 main.py"
echo ""
echo "📊 Comandi utili PostgreSQL:"
echo "   brew services stop postgresql@15   # Ferma PostgreSQL"
echo "   brew services restart postgresql@15 # Riavvia PostgreSQL"
echo "   psql -h localhost -U aivideomaker -d aivideomaker  # Connetti a DB"
echo ""
