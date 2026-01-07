/**
 * Timezone Detection and Management
 * Automatically detects user's timezone and sends it to the server
 */

(function() {
    'use strict';
    
    /**
     * Get user's timezone using Intl API
     * @returns {string} IANA timezone string (e.g., 'America/New_York')
     */
    function detectTimezone() {
        try {
            return Intl.DateTimeFormat().resolvedOptions().timeZone;
        } catch (e) {
            console.error('Failed to detect timezone:', e);
            return 'UTC';
        }
    }
    
    /**
     * Send timezone to server
     * @param {string} timezone - IANA timezone string
     */
    function saveTimezoneToServer(timezone) {
        const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value;
        
        fetch('/api/user/set-timezone/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken
            },
            body: JSON.stringify({ timezone: timezone })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                console.log('Timezone saved:', timezone);
                localStorage.setItem('user_timezone', timezone);
            } else {
                console.error('Failed to save timezone:', data.error);
            }
        })
        .catch(error => {
            console.error('Error saving timezone:', error);
        });
    }
    
    /**
     * Convert UTC datetime string to local datetime
     * @param {string} utcDatetimeStr - UTC datetime string from server
     * @returns {Date} Local Date object
     */
    function utcToLocal(utcDatetimeStr) {
        // Parse the UTC datetime string
        const utcDate = new Date(utcDatetimeStr);
        return utcDate;
    }
    
    /**
     * Format datetime in user's local timezone
     * @param {Date|string} datetime - Date object or datetime string
     * @param {Object} options - Intl.DateTimeFormat options
     * @returns {string} Formatted datetime string
     */
    function formatLocalDateTime(datetime, options = {}) {
        const date = datetime instanceof Date ? datetime : new Date(datetime);
        
        const defaultOptions = {
            year: 'numeric',
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        };
        
        const formatOptions = { ...defaultOptions, ...options };
        
        try {
            return new Intl.DateTimeFormat('en-US', formatOptions).format(date);
        } catch (e) {
            console.error('Failed to format datetime:', e);
            return date.toString();
        }
    }
    
    /**
     * Convert minutes from midnight to time string in user's timezone
     * @param {number} minutes - Minutes from midnight (0-1440)
     * @param {string} date - Date string in YYYY-MM-DD format
     * @returns {string} Time string in HH:MM format
     */
    function minutesToTime(minutes, date) {
        const hours = Math.floor(minutes / 60);
        const mins = minutes % 60;
        return `${String(hours).padStart(2, '0')}:${String(mins).padStart(2, '0')}`;
    }
    
    /**
     * Convert time string to minutes from midnight
     * @param {string} timeStr - Time string in HH:MM format
     * @returns {number} Minutes from midnight
     */
    function timeToMinutes(timeStr) {
        const [hours, minutes] = timeStr.split(':').map(Number);
        return hours * 60 + minutes;
    }
    
    /**
     * Initialize timezone detection on page load
     */
    function init() {
        // Only run for authenticated users
        if (!document.body.dataset.userAuthenticated) {
            return;
        }
        
        const detectedTimezone = detectTimezone();
        const savedTimezone = localStorage.getItem('user_timezone');
        
        // If timezone has changed or never been set, save it
        if (!savedTimezone || savedTimezone !== detectedTimezone) {
            saveTimezoneToServer(detectedTimezone);
        }
    }
    
    // Export functions to global scope for use in templates
    window.TimezoneHelper = {
        detectTimezone,
        saveTimezoneToServer,
        utcToLocal,
        formatLocalDateTime,
        minutesToTime,
        timeToMinutes
    };
    
    // Auto-initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
