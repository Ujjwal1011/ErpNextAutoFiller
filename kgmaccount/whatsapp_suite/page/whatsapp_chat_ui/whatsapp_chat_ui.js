frappe.pages['whatsapp-chat-ui'].on_page_load = function(wrapper) {
    const page = frappe.ui.make_app_page({
        parent: wrapper,
        title: 'WhatsApp Chat',
        single_column: true
    });
    const fullScreenMode = new URLSearchParams(window.location.search).get('fullscreen') === '1';

    $('body').toggleClass('wa-chat-fullscreen', fullScreenMode);
    if (!fullScreenMode) {
        page.add_inner_button(__('Open Full-Screen Tab'), function() {
            window.open('/app/whatsapp-chat-ui?fullscreen=1', '_blank', 'noopener');
        });
    }

    const $main = $(wrapper).find('.layout-main-section');
    let selectedGroup = null;
    let chatHistoryOffset = 0;
    let storedHistoryHasMore = false;

    $main.html(`
        <style>
            body.wa-chat-fullscreen { overflow: hidden; }
            body.wa-chat-fullscreen > .navbar,
            body.wa-chat-fullscreen .page-head { display: none !important; }
            body.wa-chat-fullscreen .page-body { width: 100%; max-width: none; padding: 8px; }
            body.wa-chat-fullscreen .layout-side-section { display: none !important; }
            body.wa-chat-fullscreen .layout-main-section-wrapper { flex: 0 0 100%; max-width: 100%; }
            body.wa-chat-fullscreen .wa-chat-shell { height: calc(100vh - 16px); min-height: 0; }
            .wa-chat-shell { display: grid; grid-template-columns: 330px minmax(0, 1fr); height: calc(100vh - 158px); min-height: 420px; border: 1px solid #dfe5eb; border-radius: 8px; overflow: hidden; background: #ffffff; }
            .wa-sidebar { min-height: 0; border-right: 1px solid #dfe5eb; background: #f8fafc; overflow-y: auto; }
            .wa-sidebar-head { padding: 12px 14px; border-bottom: 1px solid #dfe5eb; display: flex; align-items: center; justify-content: space-between; gap: 10px; }
            .wa-title { font-weight: 700; color: #1f2933; font-size: 14px; }
            .wa-group-item { padding: 12px 14px; border-bottom: 1px solid #edf2f7; cursor: pointer; background: #ffffff; }
            .wa-group-item:hover, .wa-group-item.active { background: #ecfdf5; }
            .wa-group-name { font-weight: 700; font-size: 13px; color: #1f2933; overflow-wrap: anywhere; }
            .wa-group-meta { color: #64748b; font-size: 11px; margin-top: 4px; overflow-wrap: anywhere; }
            .wa-btn { border: 1px solid #cbd5e1; background: #ffffff; color: #334155; border-radius: 6px; padding: 7px 10px; font-size: 12px; font-weight: 700; cursor: pointer; line-height: 1.2; }
            .wa-btn:hover { background: #f1f5f9; text-decoration: none; }
            .wa-btn.primary { background: #0f766e; border-color: #0f766e; color: #ffffff; }
            .wa-btn.primary:hover { background: #115e59; }
            .wa-btn:disabled { opacity: 0.6; cursor: not-allowed; }
            .wa-chat-area { display: flex; flex-direction: column; min-width: 0; min-height: 0; overflow: hidden; background-color: #efeae2; background-image: url('https://user-images.githubusercontent.com/15075759/28719144-86dc0f70-73b1-11e7-911d-60d70fcded21.png'); }
            .wa-chat-header { flex: 0 0 auto; min-height: 58px; padding: 10px 14px; background: #ffffff; border-bottom: 1px solid #dfe5eb; display: flex; align-items: center; justify-content: space-between; gap: 12px; }
            .wa-chat-name { font-size: 14px; font-weight: 700; color: #1f2933; overflow-wrap: anywhere; }
            .wa-chat-meta { color: #64748b; font-size: 11px; margin-top: 3px; overflow-wrap: anywhere; }
            .wa-chat-box { flex: 1 1 auto; min-height: 0; padding: 18px; overflow-x: hidden; overflow-y: auto; overscroll-behavior: contain; display: flex; flex-direction: column; gap: 2px; }
            .wa-load-older-wrap { display: flex; justify-content: center; padding: 0 0 14px; }
            .wa-empty { padding: 28px; text-align: center; color: #64748b; }
            .wa-denied { max-width: 560px; margin: 60px auto; background: #ffffff; border: 1px solid #dfe5eb; border-radius: 8px; padding: 22px; text-align: center; }
            .wa-msg { max-width: min(65%, 720px); padding: 8px 12px; border-radius: 8px; margin-bottom: 8px; font-size: 13px; position: relative; box-shadow: 0 1px 1px rgba(0,0,0,0.1); overflow-wrap: anywhere; }
            .wa-incoming { background-color: #ffffff; align-self: flex-start; border-top-left-radius: 0; }
            .wa-outgoing { background-color: #dcf8c6; align-self: flex-end; border-top-right-radius: 0; }
            .wa-time { font-size: 10px; color: #667781; text-align: right; display: block; margin-top: 4px; }
            .wa-media-bubble { max-width: min(78%, 430px); padding: 6px; }
            .wa-media-link { display: block; line-height: 0; }
            .wa-media-img { display: block; width: auto; max-width: 100%; max-height: 430px; object-fit: contain; border-radius: 6px; margin-bottom: 5px; }
            .wa-audio-bubble { max-width: min(78%, 390px); }
            .wa-audio-player { display: block; width: 330px; min-width: 260px; max-width: 100%; height: 40px; margin-bottom: 5px; }
            .wa-document-link { color: #0369a1; text-decoration: none; font-weight: 700; }
            .wa-msg-row { display: flex; align-items: flex-start; gap: 10px; max-width: min(86%, 720px); margin-bottom: 8px; }
            .wa-msg-row.wa-row-incoming { align-self: flex-start; }
            .wa-msg-row.wa-row-outgoing { align-self: flex-end; flex-direction: row-reverse; }
            .wa-msg-row .wa-msg { align-self: auto; margin-bottom: 0; }
            .wa-linked-docs { display: flex; flex-direction: column; gap: 8px; min-width: 250px; max-width: 310px; padding-top: 2px; }
            .wa-linked-doc-row { display: flex; flex-direction: column; gap: 6px; padding: 6px; border-radius: 8px; background: rgba(255, 255, 255, 0.7); border: 1px solid rgba(209, 216, 221, 0.8); }
            .wa-linked-doc-main { display: flex; align-items: center; gap: 6px; min-width: 0; }
            .wa-doc-btn { display: inline-flex; align-items: center; justify-content: flex-start; min-width: 0; min-height: 30px; padding: 5px 9px; border: 1px solid #d1d8dd; border-radius: 6px; background: #ffffff; color: #0369a1; font-size: 12px; font-weight: 700; line-height: 1.25; text-decoration: none; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
            .wa-doc-btn:hover { background: #eaf6ff; border-color: #8ecbf0; color: #075985; text-decoration: none; }
            .wa-pill { display: inline-flex; align-items: center; min-height: 22px; padding: 3px 8px; border-radius: 999px; background: #eef2f7; color: #52616f; font-size: 11px; font-weight: 700; }
            .wa-pill.on { background: #dcfce7; color: #166534; }
            .wa-pill.off { background: #fee2e2; color: #991b1b; }
            .wa-pill.pending { background: #fef3c7; color: #92400e; }
            @media (max-width: 900px) {
                .wa-chat-shell { grid-template-columns: 1fr; }
                .wa-sidebar { border-right: 0; border-bottom: 1px solid #dfe5eb; max-height: 260px; }
                .wa-msg, .wa-msg-row { max-width: 92%; }
                .wa-msg-row, .wa-msg-row.wa-row-outgoing { flex-direction: column; }
                .wa-linked-docs { min-width: 0; max-width: none; width: 100%; }
            }
        </style>
        <div class="wa-chat-shell">
            <div class="wa-sidebar" id="wa-sidebar-list">
                <div class="wa-empty">Loading groups...</div>
            </div>
            <div class="wa-chat-area" id="wa-chat-main">
                <div class="wa-empty">Select a group to view messages.</div>
            </div>
        </div>
    `);

    load_groups();

    function escape_html(value) {
        return $('<div>').text(value || '').html();
    }

    function get_form_url(doctype, name) {
        const route = frappe.router && frappe.router.slug
            ? frappe.router.slug(doctype)
            : doctype.toLowerCase().replace(/\s+/g, '-');
        return `/app/${route}/${encodeURIComponent(name)}`;
    }

    function doc_link(doctype, name, label) {
        if (!name) return '';
        return `<a href="${get_form_url(doctype, name)}" target="_blank" class="wa-doc-btn">${escape_html(label || name)}</a>`;
    }

    function load_groups() {
        frappe.call({
            method: 'kgmaccount.whatsapp_suite.page.whatsapp_chat_ui.whatsapp_chat_ui.get_groups',
            callback: function(r) {
                const payload = r.message || {};
                const groups = payload.groups || [];
                const $sidebar = $('#wa-sidebar-list');

                if (!payload.can_access) {
                    $('#wa-chat-main').html(`
                        <div class="wa-denied">
                            <div class="wa-title">WhatsApp access is not enabled</div>
                            <div class="wa-group-meta">Ask a System Manager to add your user in WhatsApp User Access.</div>
                        </div>
                    `);
                    $sidebar.html('<div class="wa-empty">No access</div>');
                    return;
                }

                $sidebar.html(`
                    <div class="wa-sidebar-head">
                        <div class="wa-title">Groups</div>
                        <button class="wa-btn" id="wa-refresh-groups">Refresh</button>
                    </div>
                    ${groups.length ? groups.map(groupItemHtml).join('') : '<div class="wa-empty">No groups assigned.</div>'}
                `);

                $('#wa-refresh-groups').on('click', load_groups);
                $('.wa-group-item').on('click', function() {
                    selectedGroup = groups.find(group => group.name === $(this).data('id'));
                    $('.wa-group-item').removeClass('active');
                    $(this).addClass('active');
                    if (selectedGroup) load_chat(selectedGroup);
                });

                if (!selectedGroup && groups.length) {
                    selectedGroup = groups[0];
                    $(`.wa-group-item[data-id="${selectedGroup.name}"]`).addClass('active');
                    load_chat(selectedGroup);
                }
            }
        });
    }

    function groupItemHtml(group) {
        const displayName = group.group_name || group.name;
        const active = selectedGroup && selectedGroup.name === group.name ? 'active' : '';
        const enabled = group.scraping_enabled ? '<span class="wa-pill on">Enabled</span>' : '<span class="wa-pill off">Disabled</span>';
        return `
            <div class="wa-group-item ${active}" data-id="${escape_html(group.name)}">
                <div class="wa-group-name">${escape_html(displayName)}</div>
                <div class="wa-group-meta">${escape_html(group.whatsapp_connection || 'No connection')} · ${enabled}</div>
            </div>
        `;
    }

    function load_chat(group) {
        chatHistoryOffset = 0;
        storedHistoryHasMore = false;
        const displayName = group.group_name || group.name;
        $('#wa-chat-main').html(`
            <div class="wa-chat-header">
                <div>
                    <div class="wa-chat-name">${escape_html(displayName)}</div>
                    <div class="wa-chat-meta">${escape_html(group.name)} · ${escape_html(group.whatsapp_connection || 'No connection')}</div>
                </div>
                <button class="wa-btn primary" id="wa-fetch-btn">Fetch Messages</button>
            </div>
            <div class="wa-chat-box" id="wa-chat-box-inner">
                <div class="wa-empty">Loading chat...</div>
            </div>
        `);

        $('#wa-fetch-btn').on('click', function() {
            fetchGroupMessages(group.name);
        });

        fetch_messages_to_ui(group.name, false);
    }

    function fetchGroupMessages(groupName) {
        const $btn = $('#wa-fetch-btn');
        $btn.prop('disabled', true).text('Fetching...');
        frappe.call({
            method: 'kgmaccount.whatsapp_suite.doctype.whatsapp_group.whatsapp_group.fetch_group_messages',
            args: { group_docname: groupName },
            callback: function(r) {
                const msg = r.message && r.message.message ? r.message.message : 'Fetch complete.';
                const success = r.message && r.message.status === 'success';
                frappe.show_alert({ message: msg, indicator: success ? 'green' : 'red' });
                if (!success) {
                    frappe.msgprint({
                        title: __('WhatsApp Server Unavailable'),
                        indicator: 'red',
                        message: msg
                    });
                    return;
                }
                fetch_messages_to_ui(groupName, false);
            },
            always: function() {
                $btn.prop('disabled', false).text('Fetch Messages');
            }
        });
    }

    function fetch_messages_to_ui(groupName, loadOlder) {
        const $box = $('#wa-chat-box-inner');
        const start = loadOlder ? chatHistoryOffset : 0;
        const oldHeight = loadOlder && $box[0] ? $box[0].scrollHeight : 0;
        const oldScrollTop = loadOlder && $box[0] ? $box[0].scrollTop : 0;

        if (loadOlder) {
            $box.find('.wa-load-older').prop('disabled', true).text('Loading...');
        }

        frappe.call({
            method: 'kgmaccount.whatsapp_suite.page.whatsapp_chat_ui.whatsapp_chat_ui.get_chat_history',
            args: { group_name: groupName, start: start },
            callback: function(r) {
                if (!selectedGroup || selectedGroup.name !== groupName) return;

                const payload = r.message || {};
                const messages = payload.messages || [];
                storedHistoryHasMore = Boolean(payload.has_more);
                if (!messages.length) {
                    if (!loadOlder) {
                        $box.html('<div class="wa-empty">No messages in this chat yet.</div>');
                    } else {
                        $box.find('.wa-load-older-wrap').remove();
                    }
                    return;
                }

                const messagesHtml = messages.map(messageHtml).join('');
                if (loadOlder) {
                    $box.find('.wa-load-older-wrap').remove();
                    $box.prepend(messagesHtml);
                    chatHistoryOffset += messages.length;
                    $box.prepend(loadOlderButtonHtml(payload.has_more));

                    const box = $box[0];
                    box.scrollTop = oldScrollTop + (box.scrollHeight - oldHeight);
                    let trackedHeight = box.scrollHeight;
                    $box.find('img, video').slice(0, messages.length).on('load loadedmetadata', function() {
                        const heightChange = box.scrollHeight - trackedHeight;
                        box.scrollTop += heightChange;
                        trackedHeight = box.scrollHeight;
                    });
                } else {
                    $box.html(`${loadOlderButtonHtml(payload.has_more)}${messagesHtml}`);
                    chatHistoryOffset = messages.length;

                    // Media loads after the message HTML and can increase the chat height.
                    // Keep the initial view pinned to the newest message as that happens.
                    scroll_to_latest($box);
                    $box.find('img, video').on('load loadedmetadata', function() {
                        scroll_to_latest($box);
                    });
                }

                $box.find('.wa-load-older').off('click').on('click', function() {
                    load_older_messages(groupName);
                });
            }
        });
    }

    function load_older_messages(groupName) {
        if (!storedHistoryHasMore) return;
        fetch_messages_to_ui(groupName, true);
    }

    function loadOlderButtonHtml(hasMore) {
        const disabled = hasMore ? '' : 'disabled';
        const label = hasMore ? 'Load Older Messages' : 'No Older Messages';
        return `<div class="wa-load-older-wrap"><button class="wa-btn wa-load-older" ${disabled}>${label}</button></div>`;
    }

    function scroll_to_latest($box) {
        const box = $box && $box[0];
        if (!box) return;

        requestAnimationFrame(() => {
            box.scrollTop = box.scrollHeight;
        });
        setTimeout(() => {
            box.scrollTop = box.scrollHeight;
        }, 100);
    }

    function messageHtml(msg) {
        const bubble = msg.direction === 'Outgoing' ? 'wa-outgoing' : 'wa-incoming';
        const time = msg.timestamp ? moment(msg.timestamp).format('MMM D, hh:mm A') : '';
        let mediaClass = '';
        if (msg.has_media && ['Image', 'Video'].includes(msg.media_type)) mediaClass = 'wa-media-bubble';
        if (msg.has_media && msg.media_type === 'Audio') mediaClass = 'wa-audio-bubble';

        let mediaHtml = '';
        if (msg.has_media && msg.attachment) {
            const attachment = escape_html(msg.attachment);
            if (msg.media_type === 'Image') {
                mediaHtml += `<a href="${attachment}" target="_blank" class="wa-media-link"><img src="${attachment}" class="wa-media-img" loading="lazy" /></a>`;
            } else if (msg.media_type === 'Video') {
                mediaHtml += `<video src="${attachment}" controls class="wa-media-img"></video>`;
            } else if (msg.media_type === 'Audio') {
                mediaHtml += `<audio src="${attachment}" controls class="wa-audio-player"></audio>`;
            } else {
                mediaHtml += `<a href="${attachment}" target="_blank" class="wa-document-link">View ${escape_html(msg.media_type || 'Attachment')}</a><br>`;
            }
        }

        const safeText = msg.message ? escape_html(msg.message).replace(/\n/g, '<br>') : '';
        const textHtml = safeText ? `<div>${safeText}</div>` : '';
        let html = `<div class="wa-msg ${bubble} ${mediaClass}">${mediaHtml}${textHtml}<span class="wa-time">${time}</span></div>`;
        const linkedDocsHtml = render_staging_links(msg.order_staging_links);

        if (linkedDocsHtml && mediaHtml && msg.media_type !== 'Audio') {
            const rowClass = msg.direction === 'Outgoing' ? 'wa-row-outgoing' : 'wa-row-incoming';
            return `<div class="wa-msg-row ${rowClass}">${html}${linkedDocsHtml}</div>`;
        }

        return linkedDocsHtml ? html.replace('</div>', `${linkedDocsHtml}</div>`) : html;
    }

    function render_staging_links(stagingLinks) {
        if (!stagingLinks || !stagingLinks.length) return '';

        const rows = stagingLinks.map(row => {
            const status = row.status || 'Pending';
            const statusClass = status === 'Converted' ? 'on' : status === 'Failed' ? 'off' : 'pending';
            return `
                <div class="wa-linked-doc-row">
                    <div class="wa-linked-doc-main">
                        ${doc_link('WhatsApp Order Staging', row.name, `Order Staging ${row.name}`)}
                        <span class="wa-pill ${statusClass}">${escape_html(status)}</span>
                    </div>
                    ${row.created_sales_order ? doc_link('Sales Order', row.created_sales_order, `Sales Order ${row.created_sales_order}`) : ''}
                </div>
            `;
        }).join('');

        return `<div class="wa-linked-docs">${rows}</div>`;
    }
};

frappe.pages['whatsapp-chat-ui'].on_page_show = function() {
    const fullScreenMode = new URLSearchParams(window.location.search).get('fullscreen') === '1';
    $('body').toggleClass('wa-chat-fullscreen', fullScreenMode);
};

frappe.pages['whatsapp-chat-ui'].on_page_hide = function() {
    $('body').removeClass('wa-chat-fullscreen');
};
