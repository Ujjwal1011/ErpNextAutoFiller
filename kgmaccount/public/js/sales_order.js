frappe.ui.form.on("Sales Order", {
	refresh(frm) {
		render_ai_image_viewer(frm);
	},

	custom_ai_cropped_image(frm) {
		render_ai_image_viewer(frm);
	},
});

function render_ai_image_viewer(frm) {
	const field = frm.get_field("custom_ai_cropped_image");
	if (!field || !field.$wrapper) return;

	field.$wrapper.find(".kgm-ai-image-viewer").remove();

	const image_url = frm.doc.custom_ai_cropped_image;
	if (!image_url) return;

	const $viewer = $("<div>", {
		class: "kgm-ai-image-viewer border rounded p-3 text-center mt-3",
	}).css({
		width: "420px",
		height: "420px",
		"max-width": "100%",
		background: "var(--subtle-fg)",
		display: "flex",
		"flex-direction": "column",
		"justify-content": "center",
	}).appendTo(field.$wrapper);

	const $link = $("<a>", {
		href: image_url,
		target: "_blank",
		rel: "noopener noreferrer",
		title: __("Open full-size image"),
	}).appendTo($viewer);

	$("<img>", {
		src: image_url,
		alt: __("Cropped WhatsApp order image"),
		class: "rounded",
	}).css({
		width: "100%",
		height: "350px",
		"object-fit": "contain",
		cursor: "zoom-in",
	}).appendTo($link);

	$("<div>", { class: "mt-2" })
		.append(
			$("<a>", {
				href: image_url,
				target: "_blank",
				rel: "noopener noreferrer",
				class: "btn btn-xs btn-default",
				text: __("Open Full Size"),
			})
		)
		.appendTo($viewer);
}
