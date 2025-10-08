/**
 * Wildcard Simulator - Hybrid Storage Manager
 * 
 * Strategy:
 * 1. Auto-save to localStorage (instant, free)
 * 2. Create minimal DB entry for tracking on first interaction
 * 3. Full save to DB only when user clicks "Save & Share"
 */

class WildcardManager {
    constructor() {
        this.storageKey = 'wildcard_draft';
        this.codeKey = 'wildcard_code';
        this.autoSaveInterval = 30000; // 30 seconds
        this.code = null;
        this.currentTeam = {
            players: [],
            formation: null,
            captain: null,
            viceCaptain: null
        };
        
        this.init();
    }
    
    async init() {
        // Check if we have a code from previous session
        this.code = localStorage.getItem(this.codeKey);
        
        if (!this.code) {
            // First time user - create tracking entry
            await this.createTrackingEntry();
        }
        
        // Load draft from localStorage
        this.loadLocalDraft();
        
        // Start auto-save
        this.startAutoSave();
        
        console.log('✅ Wildcard Manager initialized');
    }
    
    async createTrackingEntry() {
        try {
            const response = await fetch('/api/wildcard/track/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                }
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.code = data.code;
                localStorage.setItem(this.codeKey, data.code);
                console.log('📊 Team tracking started:', data.code);
            }
        } catch (error) {
            console.error('❌ Failed to create tracking entry:', error);
        }
    }
    
    loadLocalDraft() {
        const stored = localStorage.getItem(this.storageKey);
        
        if (stored) {
            try {
                const data = JSON.parse(stored);
                this.currentTeam = data.team || this.currentTeam;
                
                const savedTime = new Date(data.lastSaved);
                const timeAgo = this.formatTimeAgo(savedTime);
                
                console.log(`📂 Draft loaded (saved ${timeAgo})`);
                this.renderTeam();
                this.showNotification(`Draft restored from ${timeAgo}`);
            } catch (error) {
                console.error('Failed to parse stored draft:', error);
            }
        }
    }
    
    startAutoSave() {
        setInterval(() => {
            this.autoSave();
        }, this.autoSaveInterval);
        
        // Also save on page unload
        window.addEventListener('beforeunload', () => {
            this.autoSave();
        });
    }
    
    autoSave() {
        const data = {
            version: 1,
            lastSaved: new Date().toISOString(),
            team: this.currentTeam
        };
        
        localStorage.setItem(this.storageKey, JSON.stringify(data));
        console.log('💾 Draft auto-saved to localStorage');
        this.showAutoSaveIndicator();
    }
    
    async saveToCloud() {
        if (!this.code) {
            this.showError('No team code found. Please refresh the page.');
            return;
        }
        
        const teamName = prompt('Give your wildcard team a name (optional):');
        
        try {
            const response = await fetch(`/api/wildcard/${this.code}/save/`, {
                method: 'PATCH',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    squad_data: {
                        players: this.currentTeam.players,
                        formation: this.currentTeam.formation,
                        captain: this.currentTeam.captain,
                        viceCaptain: this.currentTeam.viceCaptain
                    },
                    team_name: teamName || ''
                })
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.showSuccessModal(data);
            } else {
                this.showError(data.error || 'Failed to save team');
            }
        } catch (error) {
            console.error('❌ Failed to save to cloud:', error);
            this.showError('Network error. Please try again.');
        }
    }
    
    async shareAsImage() {
        // Capture the team display as an image
        const teamContainer = document.querySelector('.team-display');
        if (!teamContainer) {
            this.showError('Team container not found');
            return;
        }
        
        try {
            this.showNotification('📸 Generating image...');
            
            const canvas = await html2canvas(teamContainer, {
                backgroundColor: '#37003c',
                scale: 2, // Higher quality
                logging: false
            });
            
            // Convert to blob
            canvas.toBlob((blob) => {
                const url = URL.createObjectURL(blob);
                
                // Create download link
                const link = document.createElement('a');
                link.download = `wildcard-team-${this.code || 'draft'}.png`;
                link.href = url;
                link.click();
                
                // Cleanup
                URL.revokeObjectURL(url);
                
                this.showNotification('✅ Image downloaded!');
            }, 'image/png');
            
        } catch (error) {
            console.error('❌ Failed to generate image:', error);
            this.showError('Failed to generate image. Please try again.');
        }
    }
    
    copyShareLink() {
        if (!this.code) {
            this.showError('No team code found');
            return;
        }
        
        const shareUrl = `${window.location.origin}/wildcard/${this.code}/`;
        
        // Try modern clipboard API first
        if (navigator.clipboard && navigator.clipboard.writeText) {
            navigator.clipboard.writeText(shareUrl)
                .then(() => {
                    this.showNotification('✅ Link copied to clipboard!');
                })
                .catch(() => {
                    this.fallbackCopyToClipboard(shareUrl);
                });
        } else {
            this.fallbackCopyToClipboard(shareUrl);
        }
    }
    
    fallbackCopyToClipboard(text) {
        // Fallback for older browsers
        const textarea = document.createElement('textarea');
        textarea.value = text;
        textarea.style.position = 'fixed';
        textarea.style.opacity = '0';
        document.body.appendChild(textarea);
        textarea.select();
        
        try {
            document.execCommand('copy');
            this.showNotification('✅ Link copied to clipboard!');
        } catch (err) {
            this.showError('Failed to copy link. Please copy manually.');
        }
        
        document.body.removeChild(textarea);
    }
    
    shareOnTwitter() {
        if (!this.code) {
            this.showError('No team code found');
            return;
        }
        
        const shareUrl = `${window.location.origin}/wildcard/${this.code}/`;
        const text = `Check out my FPL Wildcard team! 🔥⚽`;
        const twitterUrl = `https://twitter.com/intent/tweet?text=${encodeURIComponent(text)}&url=${encodeURIComponent(shareUrl)}`;
        
        window.open(twitterUrl, '_blank', 'width=550,height=420');
    }
    
    shareOnFacebook() {
        if (!this.code) {
            this.showError('No team code found');
            return;
        }
        
        const shareUrl = `${window.location.origin}/wildcard/${this.code}/`;
        const facebookUrl = `https://www.facebook.com/sharer/sharer.php?u=${encodeURIComponent(shareUrl)}`;
        
        window.open(facebookUrl, '_blank', 'width=550,height=420');
    }
    
    addPlayer(playerId) {
        // Add player logic
        this.currentTeam.players.push({
            id: playerId,
            // ... other player data
        });
        
        this.autoSave();
        this.renderTeam();
    }
    
    removePlayer(playerId) {
        this.currentTeam.players = this.currentTeam.players.filter(
            p => p.id !== playerId
        );
        
        this.autoSave();
        this.renderTeam();
    }
    
    setFormation(formation) {
        this.currentTeam.formation = formation;
        this.autoSave();
        this.renderTeam();
    }
    
    setCaptain(playerId) {
        this.currentTeam.captain = playerId;
        this.autoSave();
        this.renderTeam();
    }
    
    clearDraft() {
        if (confirm('Are you sure you want to clear your draft? This cannot be undone.')) {
            localStorage.removeItem(this.storageKey);
            this.currentTeam = {
                players: [],
                formation: null,
                captain: null,
                viceCaptain: null
            };
            this.renderTeam();
            this.showNotification('Draft cleared');
        }
    }
    
    // UI Helper Methods
    
    renderTeam() {
        // Implement team rendering logic
        // This will be specific to your UI
        console.log('Rendering team:', this.currentTeam);
    }
    
    showNotification(message) {
        // Simple notification
        const notification = document.createElement('div');
        notification.className = 'notification';
        notification.textContent = message;
        document.body.appendChild(notification);
        
        setTimeout(() => {
            notification.remove();
        }, 3000);
    }
    
    showAutoSaveIndicator() {
        const indicator = document.getElementById('autosave-indicator');
        if (indicator) {
            indicator.textContent = '✓ Saved';
            indicator.style.opacity = '1';
            
            setTimeout(() => {
                indicator.style.opacity = '0';
            }, 2000);
        }
    }
    
    showSuccessModal(data) {
        const shareUrl = `${window.location.origin}/wildcard/${data.code}/`;
        
        const modal = document.createElement('div');
        modal.className = 'success-modal';
        modal.id = 'success-modal';
        modal.innerHTML = `
            <div class="modal-content">
                <h2>✅ Team Saved!</h2>
                <p>Your wildcard team has been saved and is ready to share!</p>
                
                <div class="code-box">
                    <strong>Code:</strong> ${data.code}
                </div>
                
                <div class="share-url">
                    ${shareUrl}
                </div>
                
                <div class="team-stats">
                    <p><strong>Total Cost:</strong> £${data.total_cost}m</p>
                    <p><strong>Predicted Points:</strong> ${data.predicted_points}</p>
                </div>
                
                <h3 style="margin-top: 20px; margin-bottom: 10px;">Share Your Team:</h3>
                
                <div class="actions">
                    <button class="share-btn copy" onclick="wildcardManager.copyShareLink()">
                        📋 Copy Link
                    </button>
                    <button class="share-btn image" onclick="wildcardManager.shareAsImage()">
                        📸 Download Image
                    </button>
                    <button class="share-btn" onclick="wildcardManager.shareOnTwitter()">
                        � Twitter
                    </button>
                    <button class="share-btn facebook" onclick="wildcardManager.shareOnFacebook()">
                        📘 Facebook
                    </button>
                </div>
                
                <div class="actions" style="margin-top: 15px;">
                    <button onclick="wildcardManager.closeModal()">Close</button>
                </div>
                
                <p class="note">
                    💡 Your team is saved! Anyone with this link can view it.
                </p>
            </div>
        `;
        document.body.appendChild(modal);
    }
    
    closeModal() {
        const modal = document.getElementById('success-modal');
        if (modal) {
            modal.remove();
        }
    }
    
    showError(message) {
        alert(`Error: ${message}`);
    }
    
    formatTimeAgo(date) {
        const seconds = Math.floor((Date.now() - date) / 1000);
        
        if (seconds < 60) return 'just now';
        if (seconds < 3600) return `${Math.floor(seconds / 60)} minutes ago`;
        if (seconds < 86400) return `${Math.floor(seconds / 3600)} hours ago`;
        return `${Math.floor(seconds / 86400)} days ago`;
    }
}

// Initialize on page load
let wildcardManager;
document.addEventListener('DOMContentLoaded', () => {
    wildcardManager = new WildcardManager();
    wildcardManager.init();
});

// Global helper functions for modal

function copyCode(code) {
    navigator.clipboard.writeText(code).then(() => {
        alert('✅ Code copied to clipboard!');
    });
}

function shareTeam(code) {
    const url = `${window.location.origin}/wildcard/${code}/`;
    navigator.clipboard.writeText(url).then(() => {
        alert('✅ Link copied to clipboard!');
    });
}

function closeModal() {
    const modal = document.querySelector('.success-modal');
    if (modal) modal.remove();
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.wildcardManager = new WildcardManager();
});
