(function () {
    function escapeHtml(value) {
        return String(value ?? '').replace(/[&<>"']/g, (char) => ({
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;',
            "'": '&#039;',
        }[char]));
    }

    async function parsePayload(response) {
        const text = await response.text();
        if (!text) return null;
        try {
            return JSON.parse(text);
        } catch (error) {
            return { message: text };
        }
    }

    function firstString(...values) {
        for (const value of values) {
            if (typeof value === 'string' && value.trim()) return value;
        }
        return '';
    }

    function stringList(value) {
        if (!Array.isArray(value)) return [];
        return value
            .map((item) => String(item ?? '').trim())
            .filter(Boolean);
    }

    function normalize(input, options = {}) {
        const payload = input?.payload || input?.authEnvelope || input || {};
        const nested = payload?.error || {};
        const detail = payload?.detail || {};
        const status = input?.status || payload?.status || options.status || null;
        const message = firstString(
            payload.message,
            nested.message,
            typeof detail === 'string' ? detail : detail.message,
            input?.message,
            options.fallbackMessage,
            status ? `Request failed (${status})` : 'Request failed',
        );
        return {
            status,
            code: firstString(payload.error_code, nested.code, payload.code, detail.error_code, detail.code),
            message,
            nextAllowedActions: stringList(
                payload.next_allowed_actions || nested.next_allowed_actions || detail.next_allowed_actions,
            ),
            blockedFields: stringList(payload.blocked_fields || nested.blocked_fields || detail.blocked_fields),
        };
    }

    function formatText(input, options = {}) {
        const error = normalize(input, options);
        const lines = [];
        if (options.includeStatus !== false && error.status) lines.push(`HTTP ${error.status}`);
        if (error.code) lines.push(error.code);
        lines.push(error.message);
        error.nextAllowedActions.forEach((action) => lines.push(`Next action: ${action}`));
        error.blockedFields.forEach((field) => lines.push(`Blocked field: ${field}`));
        return lines.filter(Boolean).join('\n');
    }

    function renderHtml(input, options = {}) {
        const error = normalize(input, options);
        const lines = [
            error.status && options.includeStatus !== false ? `<p><strong>HTTP ${escapeHtml(error.status)}</strong></p>` : '',
            error.code ? `<p><code>${escapeHtml(error.code)}</code></p>` : '',
            `<p>${escapeHtml(error.message)}</p>`,
        ];
        if (error.nextAllowedActions.length) {
            lines.push(`<ul>${error.nextAllowedActions.map((action) => `<li>Next action: ${escapeHtml(action)}</li>`).join('')}</ul>`);
        }
        if (error.blockedFields.length) {
            lines.push(`<ul>${error.blockedFields.map((field) => `<li>Blocked field: ${escapeHtml(field)}</li>`).join('')}</ul>`);
        }
        return lines.filter(Boolean).join('');
    }

    async function errorFromResponse(response, fallbackMessage = null) {
        const payload = await parsePayload(response);
        const err = new Error(formatText(
            { payload, status: response.status },
            { fallbackMessage: fallbackMessage || `Request failed (${response.status})` },
        ));
        err.status = response.status;
        err.payload = payload;
        return err;
    }

    window.NrcApsAuthError = {
        errorFromResponse,
        formatText,
        normalize,
        renderHtml,
    };
}());
