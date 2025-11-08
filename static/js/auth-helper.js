/**
 * Auth Helper - JWT Authentication Manager
 * =========================================
 * Gestisce autenticazione JWT per AIVideoMaker:
 * - Auto-login con credenziali demo (development mode)
 * - Storage token in localStorage
 * - Auto-refresh token prima della scadenza
 * - Intercetta fetch() per aggiungere token automaticamente
 */

class AuthManager {
    constructor() {
        this.token = null;
        this.tokenExpiry = null;
        this.refreshInterval = null;

        // Storage keys
        this.TOKEN_KEY = 'aivideomaker_token';
        this.EXPIRY_KEY = 'aivideomaker_token_expiry';

        // Carica token salvato
        this.loadToken();
    }

    /**
     * Carica token da localStorage
     */
    loadToken() {
        this.token = localStorage.getItem(this.TOKEN_KEY);
        const expiry = localStorage.getItem(this.EXPIRY_KEY);

        if (expiry) {
            this.tokenExpiry = new Date(expiry);

            // Se token è scaduto, rimuovilo
            if (this.tokenExpiry < new Date()) {
                console.log('🔒 Token scaduto, rimozione...');
                this.clearToken();
            } else {
                console.log('✅ Token caricato da localStorage');
                this.startAutoRefresh();
            }
        }
    }

    /**
     * Salva token in localStorage
     */
    saveToken(token, expiryMinutes = 60) {
        this.token = token;
        this.tokenExpiry = new Date(Date.now() + expiryMinutes * 60 * 1000);

        localStorage.setItem(this.TOKEN_KEY, token);
        localStorage.setItem(this.EXPIRY_KEY, this.tokenExpiry.toISOString());

        console.log(`✅ Token salvato (scadenza: ${this.tokenExpiry.toLocaleString()})`);

        this.startAutoRefresh();
    }

    /**
     * Rimuovi token
     */
    clearToken() {
        this.token = null;
        this.tokenExpiry = null;

        localStorage.removeItem(this.TOKEN_KEY);
        localStorage.removeItem(this.EXPIRY_KEY);

        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
            this.refreshInterval = null;
        }

        console.log('🔓 Token rimosso');
    }

    /**
     * Verifica se autenticato
     */
    isAuthenticated() {
        return this.token !== null && this.tokenExpiry > new Date();
    }

    /**
     * Auto-login con credenziali demo (solo development)
     */
    async autoLoginDemo() {
        try {
            console.log('🔐 Tentativo auto-login demo...');

            // Ottieni credenziali demo da server
            const credsResponse = await fetch('/demo-credentials');

            if (!credsResponse.ok) {
                console.log('⚠️  Demo credentials non disponibili (production mode?)');
                return false;
            }

            const credentials = await credsResponse.json();

            // Login con credenziali demo
            const loginResponse = await fetch('/api/v1/auth/login', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                },
                body: new URLSearchParams({
                    username: credentials.email,
                    password: credentials.password
                })
            });

            if (!loginResponse.ok) {
                const error = await loginResponse.json();
                console.error('❌ Auto-login fallito:', error);
                return false;
            }

            const data = await loginResponse.json();

            // Salva token
            this.saveToken(data.access_token);

            console.log('✅ Auto-login demo completato');
            console.log(`   User: ${credentials.email}`);

            return true;

        } catch (error) {
            console.error('❌ Errore auto-login demo:', error);
            return false;
        }
    }

    /**
     * Login manuale
     */
    async login(email, password) {
        try {
            const response = await fetch('/api/v1/auth/login', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                },
                body: new URLSearchParams({
                    username: email,
                    password: password
                })
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'Login fallito');
            }

            const data = await response.json();
            this.saveToken(data.access_token);

            return true;

        } catch (error) {
            console.error('❌ Login error:', error);
            throw error;
        }
    }

    /**
     * Logout
     */
    logout() {
        this.clearToken();
        console.log('👋 Logout completato');
    }

    /**
     * Refresh token
     */
    async refreshToken() {
        if (!this.token) {
            console.log('⚠️  Nessun token da refreshare');
            return false;
        }

        try {
            console.log('🔄 Refresh token...');

            // Per ora ri-login con demo credentials
            // In futuro: implementare endpoint /refresh
            return await this.autoLoginDemo();

        } catch (error) {
            console.error('❌ Errore refresh token:', error);
            this.clearToken();
            return false;
        }
    }

    /**
     * Avvia auto-refresh timer
     * Refresh 5 minuti prima della scadenza
     */
    startAutoRefresh() {
        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
        }

        if (!this.tokenExpiry) {
            return;
        }

        const msUntilExpiry = this.tokenExpiry.getTime() - Date.now();
        const msUntilRefresh = msUntilExpiry - (5 * 60 * 1000); // 5 minuti prima

        if (msUntilRefresh > 0) {
            console.log(`⏰ Auto-refresh programmato tra ${Math.floor(msUntilRefresh / 1000 / 60)} minuti`);

            setTimeout(() => {
                this.refreshToken();
            }, msUntilRefresh);
        }
    }

    /**
     * Ottieni header Authorization
     */
    getAuthHeader() {
        if (!this.token) {
            return {};
        }

        return {
            'Authorization': `Bearer ${this.token}`
        };
    }

    /**
     * Fetch wrapper con auto-auth
     *
     * Usa questo invece di fetch() normale per aggiungere
     * automaticamente il token JWT a tutte le richieste.
     */
    async authFetch(url, options = {}) {
        // Aggiungi header Authorization
        options.headers = {
            ...options.headers,
            ...this.getAuthHeader()
        };

        try {
            const response = await fetch(url, options);

            // Se 401 Unauthorized, prova refresh e riprova
            if (response.status === 401 && this.token) {
                console.log('⚠️  401 Unauthorized, tentativo refresh...');

                const refreshed = await this.refreshToken();

                if (refreshed) {
                    // Riprova richiesta con nuovo token
                    options.headers = {
                        ...options.headers,
                        ...this.getAuthHeader()
                    };

                    return await fetch(url, options);
                } else {
                    // Refresh fallito, redirect a login
                    console.error('❌ Refresh fallito, autenticazione necessaria');
                    this.clearToken();
                }
            }

            return response;

        } catch (error) {
            console.error('❌ authFetch error:', error);
            throw error;
        }
    }
}

// Crea istanza globale
const authManager = new AuthManager();

// Auto-login all'avvio (solo se non già autenticato)
document.addEventListener('DOMContentLoaded', async () => {
    if (!authManager.isAuthenticated()) {
        console.log('🔐 Utente non autenticato, tentativo auto-login...');
        const success = await authManager.autoLoginDemo();

        if (!success) {
            console.log('⚠️  Auto-login fallito. Potrebbe essere richiesta autenticazione manuale.');
            // TODO: Mostra modal login se necessario
        }
    } else {
        console.log('✅ Utente già autenticato');
    }
});

// Esporta globalmente
window.authManager = authManager;
window.authFetch = (url, options) => authManager.authFetch(url, options);

console.log('🔐 Auth Manager initialized');
