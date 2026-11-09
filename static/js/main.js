/**
 * SmartQueue - Real-Time Turn Notification & Queue Poller Engine
 * Student: Yashashri Shekhar Shinde (Roll 437, PRN 24062171263077)
 * Department: Artificial Intelligence and Data Science
 */

// Track tokens that have already triggered a turn notification in this session
const notifiedTokens = new Set(
    JSON.parse(sessionStorage.getItem("smartqueue_notified_tokens") || "[]")
);

/**
 * Generates and plays a pleasant dual-harmonic notification chime using Web Audio API.
 * Requires zero external audio files and works 100% offline!
 */
function playTurnChime() {
    try {
        const AudioCtx = window.AudioContext || window.webkitAudioContext;
        if (!AudioCtx) return;
        const ctx = new AudioCtx();
        
        // Resume context if suspended (browser autoplay policy)
        if (ctx.state === 'suspended') {
            ctx.resume();
        }

        const now = ctx.currentTime;

        // Tone 1: High note (E5 = 659.25Hz)
        const osc1 = ctx.createOscillator();
        const gain1 = ctx.createGain();
        osc1.type = "sine";
        osc1.frequency.setValueAtTime(659.25, now);
        gain1.gain.setValueAtTime(0.3, now);
        gain1.gain.exponentialRampToValueAtTime(0.001, now + 0.5);
        osc1.connect(gain1);
        gain1.connect(ctx.destination);
        osc1.start(now);
        osc1.stop(now + 0.5);

        // Tone 2: Harmonic note (A5 = 880.00Hz)
        const osc2 = ctx.createOscillator();
        const gain2 = ctx.createGain();
        osc2.type = "sine";
        osc2.frequency.setValueAtTime(880.00, now + 0.15);
        gain2.gain.setValueAtTime(0.35, now + 0.15);
        gain2.gain.exponentialRampToValueAtTime(0.001, now + 0.85);
        osc2.connect(gain2);
        gain2.connect(ctx.destination);
        osc2.start(now + 0.15);
        osc2.stop(now + 0.85);

        // Tone 3: Celebratory chord resolution (C6 = 1046.5Hz)
        const osc3 = ctx.createOscillator();
        const gain3 = ctx.createGain();
        osc3.type = "triangle";
        osc3.frequency.setValueAtTime(1046.50, now + 0.32);
        gain3.gain.setValueAtTime(0.25, now + 0.32);
        gain3.gain.exponentialRampToValueAtTime(0.001, now + 1.2);
        osc3.connect(gain3);
        gain3.connect(ctx.destination);
        osc3.start(now + 0.32);
        osc3.stop(now + 1.2);
    } catch (e) {
        console.warn("[SmartQueue Audio] Could not play audio chime:", e);
    }
}

/**
 * Triggers native browser desktop notification with fallback
 */
function showBrowserNotification(tokenNumber) {
    const title = "SmartQueue – It's Your Turn!";
    const options = {
        body: `🎉 Token ${tokenNumber}: Your token has been called. Please proceed to the counter immediately!`,
        icon: "/static/favicon.ico",
        tag: `smartqueue-call-${tokenNumber}`,
        renotify: true
    };

    if ("Notification" in window && Notification.permission === "granted") {
        try {
            new Notification(title, options);
        } catch (e) {
            console.warn("[SmartQueue Notif] Browser notification failed:", e);
        }
    }
}

/**
 * Displays the prominent on-screen banner in the customer's dashboard
 */
function showOnScreenTurnBanner(tokenNumber) {
    const banner = document.getElementById("turn-notification-banner");
    const tokenSpan = document.getElementById("turn-banner-token");
    if (banner) {
        if (tokenSpan) tokenSpan.textContent = tokenNumber;
        banner.style.display = "block";
        banner.scrollIntoView({ behavior: "smooth", block: "start" });
    }
}

/**
 * Dismisses the on-screen turn banner
 */
function dismissTurnBanner() {
    const banner = document.getElementById("turn-notification-banner");
    if (banner) {
        banner.style.display = "none";
    }
}

/**
 * Handles browser notification permission request
 */
function requestNotificationPermission() {
    if (!("Notification" in window)) {
        alert("This browser does not support desktop notifications. You will still receive on-screen alerts and sounds.");
        return;
    }

    Notification.requestPermission().then(permission => {
        updateNotificationUI();
        if (permission === "granted") {
            // Play test chime and send confirmation notification
            playTurnChime();
            new Notification("SmartQueue Notifications Enabled! 🔔", {
                body: "You will be alerted the exact moment your token is called.",
                tag: "smartqueue-welcome"
            });
        }
    });
}

/**
 * Updates UI based on current Notification permission status
 */
function updateNotificationUI() {
    const btn = document.getElementById("btn-request-notif");
    const statusText = document.getElementById("notif-status-text");
    if (!btn || !statusText) return;

    if (!("Notification" in window)) {
        btn.textContent = "Notifications Unsupported";
        btn.disabled = true;
        statusText.textContent = "Your browser does not support desktop notifications. On-screen alerts and sound are active.";
        return;
    }

    if (Notification.permission === "granted") {
        btn.textContent = "✅ Notifications Active";
        btn.className = "btn btn-success btn-sm";
        btn.disabled = true;
        statusText.textContent = "Desktop notifications are enabled! You will be alerted the second your token is called.";
    } else if (Notification.permission === "denied") {
        btn.textContent = "❌ Notifications Blocked";
        btn.className = "btn btn-danger btn-sm";
        btn.disabled = true;
        statusText.textContent = "Notifications are blocked in your browser settings. Please click the padlock icon in the address bar to allow notifications.";
    } else {
        btn.textContent = "🔔 Enable Notifications";
        btn.className = "btn btn-primary btn-sm";
        btn.disabled = false;
        statusText.textContent = "Allow notifications to receive an alert and audio chime the second your token is called by the counter.";
    }
}

/**
 * Manual test button to verify audio and alert functionality
 */
function testNotification() {
    playTurnChime();
    const testTokenNumber = "DEMO-101";
    showOnScreenTurnBanner(testTokenNumber);
    
    if ("Notification" in window && Notification.permission === "granted") {
        showBrowserNotification(testTokenNumber);
    } else if ("Notification" in window && Notification.permission !== "denied") {
        requestNotificationPermission();
    }
}

/**
 * Main turn notification dispatcher: ensures sound & alerts trigger only ONCE per token
 */
function handleTurnArrival(tokenId, tokenNumber) {
    const tokenKey = tokenId.toString();
    if (notifiedTokens.has(tokenKey)) {
        return; // Prevent duplicate alerts
    }

    // Save into tracking set and sessionStorage
    notifiedTokens.add(tokenKey);
    sessionStorage.setItem("smartqueue_notified_tokens", JSON.stringify(Array.from(notifiedTokens)));

    // Trigger audio chime, desktop notification, and dashboard banner
    playTurnChime();
    showBrowserNotification(tokenNumber);
    showOnScreenTurnBanner(tokenNumber);
}

// ----------------- DOM READY INITIALIZATION ----------------- //

document.addEventListener("DOMContentLoaded", () => {
    // 1. Initialize Notification Permission UI
    updateNotificationUI();

    // 2. Auto-dismiss temporary alerts after 5 seconds
    const alerts = document.querySelectorAll(".alert");
    if (alerts.length > 0) {
        setTimeout(() => {
            alerts.forEach(alert => {
                alert.style.transition = "opacity 0.5s ease-out";
                alert.style.opacity = "0";
                setTimeout(() => alert.remove(), 500);
            });
        }, 5000);
    }

    // 3. Real-time Live Queue Poller for User Dashboard
    const liveTokenCards = document.querySelectorAll("[data-live-token-id]");
    if (liveTokenCards.length > 0) {
        console.log(`[SmartQueue] Initialized turn notification monitor for ${liveTokenCards.length} token(s).`);

        // Check already-called tokens on page load
        liveTokenCards.forEach(card => {
            const tokenId = card.getAttribute("data-live-token-id");
            const tokenNumber = card.getAttribute("data-token-number") || "Your Token";
            const currentStatus = (card.getAttribute("data-status") || "").toLowerCase();

            if (currentStatus === "called" || currentStatus === "serving") {
                showOnScreenTurnBanner(tokenNumber);
                if (!notifiedTokens.has(tokenId.toString())) {
                    handleTurnArrival(tokenId, tokenNumber);
                }
            }
        });

        // Poll server every 4 seconds for immediate notification
        setInterval(() => {
            liveTokenCards.forEach(card => {
                const tokenId = card.getAttribute("data-live-token-id");
                if (!tokenId) return;

                fetch(`/api/queue_status/${tokenId}`)
                    .then(response => {
                        if (response.status === 401 || response.status === 404) {
                            // User logged out or token completed/deleted
                            return null;
                        }
                        if (!response.ok) throw new Error("Status polling error");
                        return response.json();
                    })
                    .then(data => {
                        if (!data) return;

                        const rawStatus = (data.status || "").toLowerCase();
                        const isCalled = data.is_called || rawStatus === "called" || rawStatus === "serving";

                        // Update People Ahead
                        const peopleAheadEl = card.querySelector(".live-people-ahead");
                        if (peopleAheadEl && data.people_ahead !== undefined) {
                            peopleAheadEl.textContent = data.people_ahead;
                        }

                        // Update Serving Token
                        const servingTokenEl = card.querySelector(".live-serving-token");
                        if (servingTokenEl && data.serving_token) {
                            servingTokenEl.textContent = data.serving_token;
                        }

                        // Update Estimated Wait Time
                        const waitTimeEl = card.querySelector(".live-wait-time");
                        if (waitTimeEl && data.estimated_wait_time !== undefined) {
                            waitTimeEl.textContent = `${data.estimated_wait_time} mins`;
                        }

                        // Update Status Message Text
                        const statusMsgEl = card.querySelector(".live-status-message");
                        if (statusMsgEl && data.status_message) {
                            statusMsgEl.textContent = data.status_message;
                        }

                        // Update Status Badge Pill
                        const statusPill = card.querySelector(".token-status-pill");
                        if (statusPill && data.status) {
                            statusPill.textContent = data.status;
                            statusPill.className = `token-status-pill status-${rawStatus}`;
                        }

                        // Check for TURN ARRIVAL: status 'called' or 'serving'
                        if (isCalled) {
                            card.classList.add("token-card-called");
                            handleTurnArrival(tokenId, data.token_number);

                            // Update action button area to show Call to Action
                            const actionsDiv = card.querySelector(".token-actions");
                            if (actionsDiv && !actionsDiv.querySelector(".turn-active-msg")) {
                                actionsDiv.innerHTML = `
                                    <span class="turn-active-msg" style="color: var(--success); font-weight: 700; font-size: 1rem;">
                                        🔔 🎉 Your turn is called! Please proceed to the Counter.
                                    </span>
                                `;
                            }
                        } else if (rawStatus === "completed" || rawStatus === "skipped" || rawStatus === "cancelled") {
                            // Token finished: dismiss banner and reload to move to history
                            dismissTurnBanner();
                            card.classList.remove("token-card-called");
                            setTimeout(() => window.location.reload(), 1500);
                        }
                    })
                    .catch(err => {
                        console.debug("[SmartQueue] Polling cycle info:", err);
                    });
            });
        }, 4000); // Poll every 4 seconds
    }
});

/**
 * Confirms user cancellation of a queue token.
 */
function confirmCancelToken(tokenNumber) {
    return confirm(`Are you sure you want to cancel token ${tokenNumber}? This action cannot be undone.`);
}

/**
 * Confirms admin skip action.
 */
function confirmSkipToken(tokenNumber) {
    return confirm(`Are you sure you want to skip token ${tokenNumber}? The next waiting customer will be called.`);
}
