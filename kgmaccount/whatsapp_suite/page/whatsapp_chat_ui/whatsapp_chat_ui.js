frappe.pages['whatsapp-chat-ui'].on_page_load = function(wrapper) {
    var page = frappe.ui.make_app_page({
        parent: wrapper,
        title: 'WhatsApp Chat',
        single_column: true
    });

    // --- FULLSCREEN TWEAKS ---
    $(wrapper).find('.page-head').hide();
    $(wrapper).find('.layout-main-section').css({'padding': '0', 'margin': '0'});
    $(wrapper).find('.page-body').css({'padding': '0', 'margin': '0'});
    $('.layout-main').css({'padding-top': '0'}); 
    
    // NEW: Force Frappe's master container to stretch 100% to the right edge
    $(wrapper).closest('.container').css({'max-width': '100%', 'width': '100%', 'padding': '0'});
    // -----------------------------

    // 1. Inject the HTML & CSS Layout
    $(wrapper).find('.layout-main-section').html(`
        <style>
            .wa-container { display: flex; height: calc(100vh - 60px); width: 100%; border-top: 1px solid #d1d8dd; overflow: hidden; background: #fff; }
            .wa-sidebar { width: 30%; border-right: 1px solid #d1d8dd; background: #f0f2f5; overflow-y: auto; }
            .wa-group-item { padding: 15px; border-bottom: 1px solid #e9edef; cursor: pointer; transition: background 0.2s; }
            .wa-group-item:hover, .wa-group-item.active { background: #e9edef; }
            .wa-group-name { font-weight: bold; font-size: 15px; color: #111b21; }
            .wa-group-meta { font-size: 12px; color: #667781; margin-top: 4px; }
            
            .wa-chat-area { width: 70%; display: flex; flex-direction: column; background-image: url('https://user-images.githubusercontent.com/15075759/28719144-86dc0f70-73b1-11e7-911d-60d70fcded21.png'); background-color: #efeae2; }
            .wa-chat-header { padding: 15px; background: #f0f2f5; border-bottom: 1px solid #d1d8dd; display: flex; align-items: center; justify-content: space-between; font-weight: bold; font-size: 16px; }
            .wa-chat-box { flex: 1; padding: 20px; overflow-y: auto; display: flex; flex-direction: column; gap: 2px; }
            
            .wa-empty-state { display: flex; align-items: center; justify-content: center; height: 100%; color: #667781; font-size: 16px; background: #f0f2f5; }
            
            .wa-msg { max-width: min(65%, 720px); padding: 8px 12px; border-radius: 8px; margin-bottom: 8px; font-size: 14px; position: relative; box-shadow: 0 1px 1px rgba(0,0,0,0.1); word-wrap: break-word; overflow-wrap: anywhere; }
            .wa-incoming { background-color: #ffffff; align-self: flex-start; border-top-left-radius: 0; }
            .wa-outgoing { background-color: #dcf8c6; align-self: flex-end; border-top-right-radius: 0; }
            .wa-time { font-size: 10px; color: #999; text-align: right; display: block; margin-top: 4px; }
            .wa-media-bubble { max-width: min(78%, 430px); padding: 6px; }
            .wa-media-link { display: block; line-height: 0; }
            .wa-media-img { display: block; width: auto; max-width: 100%; max-height: 430px; object-fit: contain; border-radius: 6px; margin-bottom: 5px; transition: opacity 0.2s; }
            .wa-media-img:hover { opacity: 0.92; cursor: pointer; }
            .wa-audio-bubble { max-width: min(78%, 390px); }
            .wa-audio-player { display: block; width: 330px; min-width: 280px; max-width: 100%; height: 40px; margin-bottom: 5px; }
            .wa-document-link { color: #0275d8; text-decoration: none; font-weight: 500; }
            .wa-document-link:hover { text-decoration: underline; }
            .wa-msg-row { display: flex; align-items: flex-start; gap: 10px; max-width: min(86%, 720px); margin-bottom: 8px; }
            .wa-msg-row.wa-row-incoming { align-self: flex-start; }
            .wa-msg-row.wa-row-outgoing { align-self: flex-end; flex-direction: row-reverse; }
            .wa-msg-row .wa-msg { align-self: auto; margin-bottom: 0; }
            .wa-msg-row .wa-media-bubble { flex: 0 1 430px; }
            .wa-linked-docs { display: flex; flex-direction: column; gap: 8px; min-width: 270px; max-width: 310px; padding-top: 2px; }
            .wa-linked-doc-row { display: flex; flex-direction: column; gap: 5px; padding: 6px; border-radius: 8px; background: rgba(255, 255, 255, 0.64); border: 1px solid rgba(209, 216, 221, 0.72); box-shadow: 0 1px 2px rgba(15, 23, 42, 0.08); backdrop-filter: blur(2px); }
            .wa-linked-doc-main { display: flex; align-items: center; gap: 6px; min-width: 0; }
            .wa-doc-btn { display: inline-flex; align-items: center; justify-content: flex-start; min-width: 0; min-height: 30px; padding: 5px 9px; border: 1px solid #d1d8dd; border-radius: 6px; background: #ffffff; color: #0369a1; font-size: 12px; font-weight: 700; line-height: 1.25; text-decoration: none; box-shadow: 0 1px 1px rgba(15, 23, 42, 0.05); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
            .wa-doc-btn:hover { background: #eaf6ff; border-color: #8ecbf0; color: #075985; text-decoration: none; transform: translateY(-1px); }
            .wa-staging-btn { flex: 1 1 auto; }
            .wa-sales-order-btn { color: #047857; background: #ecfdf5; border-color: #b7ebd0; }
            .wa-sales-order-btn:hover { color: #065f46; background: #dff8ed; border-color: #86d9b4; }
            .wa-status-pill { flex: 0 0 auto; border-radius: 999px; padding: 3px 8px; background: #eef2f7; color: #52616f; font-size: 11px; font-weight: 700; line-height: 1.2; }
            .wa-status-pill.is-converted { background: #dff6dd; color: #1f7a35; }
            .wa-status-pill.is-failed { background: #fde2e1; color: #b42318; }
            @media (max-width: 900px) {
                .wa-msg-row, .wa-msg-row.wa-row-outgoing { flex-direction: column; max-width: min(78%, 430px); }
                .wa-linked-docs { min-width: 0; max-width: none; width: 100%; }
            }
            
            /* Sync Button Style */
            .wa-sync-btn { background-color: #00a884; color: white; border: none; padding: 6px 12px; border-radius: 4px; font-size: 13px; cursor: pointer; transition: 0.2s; }
            .wa-sync-btn:hover { background-color: #008f6f; }
            .wa-sync-btn:disabled { background-color: #888; cursor: not-allowed; opacity: 0.7; }
			.wa-container { 
				position: fixed; 
				top: 60px; /* Anchors it right below the black ERPNext navbar */
				left: 0; 
				right: 0; 
				bottom: 0; /* Forces it all the way to the absolute bottom of the screen */
				display: flex; 
				background: #fff; 
				z-index: 99; /* Ensures it sits above Frappe's hidden wrappers */
			}
			</style>

        <div class="wa-container">
            <div class="wa-sidebar" id="wa-sidebar-list">
                <div style="padding: 20px; text-align: center; color: #888;">Loading Groups...</div>
            </div>
            <div class="wa-chat-area" id="wa-chat-main">
                <div class="wa-empty-state">Select a group to view messages</div>
            </div>
        </div>
    `);

    load_groups();

    function escape_html(value) {
        return $('<div>').text(value || '').html();
    }

    function get_form_url(doctype, name) {
        let route = frappe.router && frappe.router.slug
            ? frappe.router.slug(doctype)
            : doctype.toLowerCase().replace(/\s+/g, '-');
        return `/app/${route}/${encodeURIComponent(name)}`;
    }

    function render_staging_links(stagingLinks) {
        if (!stagingLinks || !stagingLinks.length) return '';

        let rows = stagingLinks.map(row => {
            let status = row.status || 'Pending';
            let statusClass = status === 'Converted' ? 'is-converted' : status === 'Failed' ? 'is-failed' : '';
            let html = `
                <div class="wa-linked-doc-row">
                    <div class="wa-linked-doc-main">
                        <a href="${get_form_url('WhatsApp Order Staging', row.name)}" target="_blank" class="wa-doc-btn wa-staging-btn" title="Open WhatsApp Order Staging ${escape_html(row.name)}">Order Staging ${escape_html(row.name)}</a>
                        <span class="wa-status-pill ${statusClass}">${escape_html(status)}</span>
                    </div>
            `;

            if (row.created_sales_order) {
                html += `<a href="${get_form_url('Sales Order', row.created_sales_order)}" target="_blank" class="wa-doc-btn wa-sales-order-btn" title="Open Sales Order ${escape_html(row.created_sales_order)}">Sales Order ${escape_html(row.created_sales_order)}</a>`;
            }

            html += '</div>';
            return html;
        }).join('');

        return `<div class="wa-linked-docs">${rows}</div>`;
    }

    function load_groups() {
        frappe.call({
            method: "kgmaccount.whatsapp_suite.page.whatsapp_chat_ui.whatsapp_chat_ui.get_groups",
            callback: function(r) {
                let sidebar = $('#wa-sidebar-list');
                sidebar.empty();

                if (r.message && r.message.length > 0) {
                    r.message.forEach(group => {
                        let displayName = group.group_name || group.name;
                        let item = $(`
                            <div class="wa-group-item" data-id="${escape_html(group.name)}">
                                <div class="wa-group-name">${escape_html(displayName)}</div>
                                <div class="wa-group-meta">Connection: ${escape_html(group.whatsapp_connection)}</div>
                            </div>
                        `);

                        item.on('click', function() {
                            $('.wa-group-item').removeClass('active');
                            $(this).addClass('active');
                            load_chat(group.name, displayName);
                        });

                        sidebar.append(item);
                    });
                } else {
                    sidebar.html('<div style="padding: 20px; text-align: center; color: #888;">No Groups Found.</div>');
                }
            }
        });
    }

    function load_chat(group_id, group_name) {
        let chatArea = $('#wa-chat-main');
        
        // --- NEW: Header with the Fetch Button ---
        chatArea.html(`
            <div class="wa-chat-header">
                <div>${escape_html(group_name)}</div>
                <button class="wa-sync-btn" id="wa-fetch-btn">Fetch New Messages</button>
            </div>
            <div class="wa-chat-box" id="wa-chat-box-inner">
                <div class="text-muted" style="text-align: center; margin-top: 20px;">Loading chat...</div>
            </div>
        `);

        // --- NEW: Fetch Button Logic ---
        $('#wa-fetch-btn').on('click', function() {
            let btn = $(this);
            
            // Safety lock: Do nothing if already disabled
            if (btn.prop('disabled')) return; 

            // Disable the button and change text immediately
            btn.prop('disabled', true).text('Fetching... Please wait');

            frappe.call({
                // Ensure this path points correctly to where you wrote fetch_group_messages
                method: "kgmaccount.whatsapp_suite.doctype.whatsapp_group.whatsapp_group.fetch_group_messages",
                args: { group_docname: group_id },
                callback: function(r) {
                    // Re-enable the button
                    btn.prop('disabled', false).text('Fetch New Messages');

                    if (!r.exc) {
                        // Show a nice green success popup at the bottom right
                        let msg = r.message && r.message.message ? r.message.message : "Sync Complete!";
                        frappe.show_alert({message: msg, indicator: 'green'});
                        
                        // Instantly reload the chat to show the new messages
                        fetch_messages_to_ui(group_id);
                    } else {
                        frappe.msgprint({title: 'Error', message: 'Failed to fetch messages. Check Error Log.', indicator: 'red'});
                    }
                }
            });
        });
        
        // Initial load of messages when clicking the group
        fetch_messages_to_ui(group_id);
    }

    // Helper function to just refresh the message bubbles without redrawing the header
    function fetch_messages_to_ui(group_id) {
        let box = $('#wa-chat-box-inner');
        
        frappe.call({
            method: "kgmaccount.whatsapp_suite.page.whatsapp_chat_ui.whatsapp_chat_ui.get_chat_history",
            args: { group_name: group_id },
            callback: function(r) {
                box.empty();

                if (r.message && r.message.length > 0) {
                    r.message.forEach(msg => {
                        let bubble = msg.direction === 'Outgoing' ? 'wa-outgoing' : 'wa-incoming';
                        let time = msg.timestamp ? moment(msg.timestamp).format('MMM D, hh:mm A') : "";
                        let mediaClass = msg.has_media && msg.media_type === 'Image' ? 'wa-media-bubble' : '';
                        if (msg.has_media && msg.media_type === 'Video') mediaClass = 'wa-media-bubble';
                        if (msg.has_media && msg.media_type === 'Audio') mediaClass = 'wa-audio-bubble';
                        let linkedDocsHtml = render_staging_links(msg.order_staging_links);
                        
                        let html = `<div class="wa-msg ${bubble} ${mediaClass}">`;
                        let mediaHtml = '';
                        
                        if (msg.has_media && msg.attachment) {
                            let attachment = escape_html(msg.attachment);
                            if (msg.media_type === 'Image') {
                                mediaHtml += `<a href="${attachment}" target="_blank" class="wa-media-link" title="Open image">
                                            <img src="${attachment}" class="wa-media-img" loading="lazy" />
                                         </a>`;
                            }
                            else if (msg.media_type === 'Video') mediaHtml += `<video src="${attachment}" controls class="wa-media-img"></video>`;
                            else if (msg.media_type === 'Audio') mediaHtml += `<audio src="${attachment}" controls class="wa-audio-player"></audio>`;
                            else mediaHtml += `<a href="${attachment}" target="_blank" class="wa-document-link">View ${escape_html(msg.media_type || 'Attachment')}</a><br>`;
                        }
                        
                        let safe_text = msg.message ? escape_html(msg.message).replace(/\n/g, '<br>') : '';
                        let textHtml = safe_text ? `<div style="margin-bottom: 2px;">${safe_text}</div>` : '';

                        html += mediaHtml + textHtml;
                        
                        html += `<span class="wa-time">${time}</span></div>`;

                        if (linkedDocsHtml && mediaHtml && msg.media_type !== 'Audio') {
                            let rowClass = msg.direction === 'Outgoing' ? 'wa-row-outgoing' : 'wa-row-incoming';
                            box.append(`<div class="wa-msg-row ${rowClass}">${html}${linkedDocsHtml}</div>`);
                        } else {
                            html += linkedDocsHtml;
                            box.append(html);
                        }
                    });

                    setTimeout(() => { box.scrollTop(box[0].scrollHeight); }, 50);
                } else {
                    box.html('<div class="text-muted" style="text-align: center; margin-top: 20px;">No messages in this chat yet.</div>');
                }
            }
        });
    }
};
