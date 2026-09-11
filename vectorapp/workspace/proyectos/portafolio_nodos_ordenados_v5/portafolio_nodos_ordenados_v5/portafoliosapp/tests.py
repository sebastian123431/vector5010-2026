import json
from pathlib import Path

from django.test import TestCase


class PortfolioViewTests(TestCase):
    def test_every_node_has_professional_content(self):
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        bubbles = json.loads(response.context["bubbles_json"])
        self.assertGreaterEqual(len(bubbles), 7)

        for node in bubbles:
            self.assertTrue(
                node.get("content") or node.get("text") or node.get("description") or node.get("sections"),
                msg=f'El nodo "{node.get("label", node.get("id"))}" no tiene contenido.',
            )
            for child in node.get("children", []):
                self.assertTrue(
                    child.get("text") or child.get("content") or child.get("description") or child.get("sections"),
                    msg=f'El subnodo "{child.get("label")}" no tiene contenido.',
                )

    def test_positioning_and_main_actions_are_not_duplicated(self):
        response = self.client.get("/")

        self.assertContains(response, "Desarrollador Backend Python/Django y Full Stack")
        self.assertContains(response, "Sistemas web, APIs REST y aplicaciones Android offline-first.")
        self.assertContains(response, "Construyo sistemas que no pierden datos")
        self.assertContains(response, "Python · Django · Kotlin · SQL Server")
        self.assertNotContains(response, 'class="quick-actions"')
        self.assertNotContains(response, "Ver proyectos")
        self.assertNotContains(response, 'data-node-target="github"')

    def test_controlbins_is_featured_as_main_case(self):
        response = self.client.get("/")
        bubbles = json.loads(response.context["bubbles_json"])
        projects = next(node for node in bubbles if node["id"] == "projects")
        self.assertFalse(any(node.get("id") == "controlbins" for node in bubbles))
        case = projects["children"][0]

        self.assertEqual(case["label"], "ControlBins")
        self.assertEqual(case["badge"], "Caso principal")
        self.assertIn("adoptar por los equipos operativos", case["content"])
        self.assertIn("100% de trazabilidad digitalizada", case["sections"][3]["items"][0])
        self.assertIn("Offline-first", case["tags"])
        self.assertEqual(
            case["architecture"],
            ["Android Kotlin", "SQLite offline", "Django REST API", "SQL Server", "Reportes operativos"],
        )
        self.assertEqual(case["gallery"], [])
        self.assertIn("simulation", case)
        self.assertEqual(case["simulation"]["steps"][2]["label"], "Guardado sin conexión")
        self.assertIn("SQLite/Room", case["simulation"]["steps"][2]["detail"])
        self.assertEqual(case["simulation"]["title"], "Flujo real de sincronización")

    def test_experience_and_skills_are_grouped(self):
        response = self.client.get("/")
        bubbles = json.loads(response.context["bubbles_json"])
        tech = next(node for node in bubbles if node["id"] == "tech")
        experience = next(node for node in bubbles if node["id"] == "experience")
        job = experience["children"][0]

        self.assertEqual(
            [item["label"] for item in tech["children"]],
            ["Backend", "Mobile", "Datos", "Herramientas", "Infraestructura"],
        )
        self.assertEqual([section["heading"] for section in job["sections"]], ["Desarrollo de software", "Soporte e infraestructura"])
        for skill in tech["children"]:
            self.assertTrue(skill.get("sections"), msg=f'La habilidad "{skill["label"]}" necesita secciones descriptivas.')
            self.assertTrue(skill.get("tags"), msg=f'La habilidad "{skill["label"]}" necesita tags técnicos.')
            self.assertGreater(len(skill["text"]), 80)

    def test_leaf_nodes_keep_description_even_with_sections(self):
        base_dir = Path(__file__).resolve().parents[1]
        script = (base_dir / "static" / "portafoliosapp" / "js" / "main.js").read_text(encoding="utf-8")

        self.assertIn("const valueHTML = leafDescription && !items.length", script)
        self.assertNotIn("leafDescription && !items.length && !data.sections", script)

    def test_certificates_have_professional_context_and_evidence_slots(self):
        response = self.client.get("/")
        bubbles = json.loads(response.context["bubbles_json"])
        education = next(node for node in bubbles if node["id"] == "education")
        credentials = [node for node in education["children"] if node.get("kind") in {"certificate", "degree"}]

        self.assertGreaterEqual(len(credentials), 6)
        for credential in credentials:
            self.assertIn("issuer", credential)
            self.assertIn("date", credential)
            self.assertIn("evidence", credential)
            self.assertIn("/static/portafoliosapp/images/certificates/", credential["evidence"]["src"])
            self.assertTrue(credential.get("sections"))

    def test_route_requests_location_only_from_education_action(self):
        response = self.client.get("/")
        bubbles = json.loads(response.context["bubbles_json"])
        education = next(node for node in bubbles if node["id"] == "education")
        campus = education["children"][0]

        self.assertTrue(campus["route"])
        self.assertIn("route_destination_lat", campus)
        self.assertIn("route_destination_lng", campus)
        self.assertIn("route_fallback_origin_lat", campus)
        self.assertIn("route_fallback_origin_lng", campus)
        self.assertIn("La ruta se calcula solo si el visitante decide compartir su ubicación.", campus["text"])

    def test_certificate_image_viewer_supports_zoom_controls(self):
        base_dir = Path(__file__).resolve().parents[1]
        script = (base_dir / "static" / "portafoliosapp" / "js" / "main.js").read_text(encoding="utf-8")
        styles = (base_dir / "static" / "portafoliosapp" / "css" / "style.css").read_text(encoding="utf-8")

        self.assertIn("data-image-preview", script)
        self.assertIn('data-image-zoom="in"', script)
        self.assertIn('data-image-zoom="out"', script)
        self.assertIn("handleImageWheel", script)
        self.assertIn("handleImageDoubleClick", script)
        self.assertIn("handleImageTouchMove", script)
        self.assertIn(".image-viewport.is-zoomed", styles)

    def test_mobile_layout_reserves_space_for_detail_panel(self):
        base_dir = Path(__file__).resolve().parents[1]
        script = (base_dir / "static" / "portafoliosapp" / "js" / "main.js").read_text(encoding="utf-8")
        styles = (base_dir / "static" / "portafoliosapp" / "css" / "style.css").read_text(encoding="utf-8")

        self.assertIn("--mobile-panel-height", styles)
        self.assertIn("body.panel-open .bubble-scene", styles)
        self.assertIn("body.panel-collapsed .bubble-scene", styles)
        self.assertIn("body.panel-open .bubble", styles)
        self.assertIn("panel-collapsed", script)
        self.assertIn('!document.body.classList.contains("panel-collapsed")', script)
        self.assertIn("function isPanelExpanded", script)
        self.assertIn("phone && panelOpen", script)
        self.assertIn("function solidifyLayout", script)
        self.assertIn("parentObstacle", script)
        self.assertIn("function mobilePortraitChildrenPoints", script)
        self.assertIn("function childrenParentY", script)
        self.assertIn("--module-parent-size", styles)
        self.assertIn("height: calc(var(--viewport-height, 100svh) - var(--mobile-panel-height) - 0.75rem)", styles)
        self.assertIn("body.panel-open .bubble.child.module-child .level-tag", styles)
        self.assertIn("body.panel-collapsed .bubble.child.module-child .level-tag", styles)

    def test_home_nodes_keep_readable_labels_on_tablet_layout(self):
        base_dir = Path(__file__).resolve().parents[1]
        script = (base_dir / "static" / "portafoliosapp" / "js" / "main.js").read_text(encoding="utf-8")
        styles = (base_dir / "static" / "portafoliosapp" / "css" / "style.css").read_text(encoding="utf-8")

        self.assertIn("text-wrap: balance", styles)
        self.assertIn("max-width: calc(var(--bubble-size) * 0.76)", styles)
        self.assertIn("landscape ? Math.min(rect.width * 0.35, 285)", script)
        self.assertNotIn("-webkit-line-clamp: 2;\n}", styles[styles.find(".bubble .label"):styles.find(".bubble .micro")])

    def test_portfolio_uses_custom_green_alien_tech_theme(self):
        base_dir = Path(__file__).resolve().parents[1]
        script = (base_dir / "static" / "portafoliosapp" / "js" / "main.js").read_text(encoding="utf-8")
        styles = (base_dir / "static" / "portafoliosapp" / "css" / "style.css").read_text(encoding="utf-8")
        bio_styles = (base_dir / "static" / "portafoliosapp" / "DigitalPortrait" / "DigitalPortrait.css").read_text(encoding="utf-8")

        self.assertIn("--green: #39ff14", styles)
        self.assertIn("--omni-core: #9dff2f", styles)
        self.assertIn("--rex-orange: #ff8a1c", styles)
        self.assertIn("--rex-blue: #00e6ff", styles)
        self.assertIn("conic-gradient(from 45deg", styles)
        self.assertIn("border-radius: 0.75rem", styles[styles.find(".bubble .icon"):styles.find(".bubble .node-image")])
        self.assertIn("--accent-color: #39ff14", bio_styles)
        self.assertIn("--rex-orange: #ff8a1c", bio_styles)
        self.assertIn("255, 138, 28", script)
        self.assertIn("0, 230, 255", script)

    def test_child_module_nodes_use_readable_compact_sizing(self):
        base_dir = Path(__file__).resolve().parents[1]
        script = (base_dir / "static" / "portafoliosapp" / "js" / "main.js").read_text(encoding="utf-8")
        styles = (base_dir / "static" / "portafoliosapp" / "css" / "style.css").read_text(encoding="utf-8")
        module_block = styles[styles.find(".bubble.child.module-child .bubble-content"):styles.find(".detail-panel")]

        self.assertIn('variant.includes("module-child")', script)
        self.assertIn('styles.getPropertyValue("--module-child-size")', script)
        self.assertIn("display: none", module_block)
        self.assertIn("clamp(4.8rem", styles)
        self.assertIn("clamp(4.2rem", styles)

    def test_compact_nodes_do_not_truncate_labels_with_ellipsis(self):
        base_dir = Path(__file__).resolve().parents[1]
        script = (base_dir / "static" / "portafoliosapp" / "js" / "main.js").read_text(encoding="utf-8")
        styles = (base_dir / "static" / "portafoliosapp" / "css" / "style.css").read_text(encoding="utf-8")
        mobile_block = styles[styles.find("@media (max-width: 520px)"):styles.find("@media (max-height: 430px)")]

        self.assertIn("const compactNodeLabels", script)
        self.assertIn('"Infraestructura": ["Infraestructura"]', script)
        self.assertIn('"Habilidades técnicas": ["Habilidades", "técnicas"]', script)
        self.assertIn('"Asistente de Informática": ["Asistente", "de Informática"]', script)
        self.assertIn('"CCNAv7: Introduction to Networks": ["CCNAv7:", "Introduction", "to Networks"]', script)
        self.assertIn("nodeLabelHTML(data, variant)", script)
        self.assertIn("overflow-wrap: anywhere", mobile_block)
        self.assertNotIn("text-overflow: ellipsis", mobile_block)

    def test_layout_freezes_during_browser_or_phone_zoom(self):
        base_dir = Path(__file__).resolve().parents[1]
        script = (base_dir / "static" / "portafoliosapp" / "js" / "main.js").read_text(encoding="utf-8")

        self.assertIn("layoutViewport", script)
        self.assertIn("shouldFreezeForZoom", script)
        self.assertIn("window.visualViewport?.scale", script)
        self.assertIn("viewport:zoom-freeze", script)
        self.assertIn("if (!refreshLayoutViewport())", script)

    def test_animation_runtime_has_performance_guards(self):
        base_dir = Path(__file__).resolve().parents[1]
        main_script = (base_dir / "static" / "portafoliosapp" / "js" / "main.js").read_text(encoding="utf-8")
        portrait_script = (base_dir / "static" / "portafoliosapp" / "DigitalPortrait" / "DigitalPortrait.js").read_text(encoding="utf-8")
        graph_generator = (base_dir / "static" / "portafoliosapp" / "DigitalPortrait" / "graphGenerator.js").read_text(encoding="utf-8")
        graph_renderer = (base_dir / "static" / "portafoliosapp" / "DigitalPortrait" / "graphRenderer.js").read_text(encoding="utf-8")
        image_sampler = (base_dir / "static" / "portafoliosapp" / "DigitalPortrait" / "imageSampler.js").read_text(encoding="utf-8")
        opencv_enhancer = (base_dir / "static" / "portafoliosapp" / "DigitalPortrait" / "openCvEnhancer.js").read_text(encoding="utf-8")

        self.assertIn("const enableLayoutLogs = false", main_script)
        self.assertIn("IntersectionObserver", portrait_script)
        self.assertIn("normalizeProgress", portrait_script)
        self.assertIn("progress >= 0.965 ? 1", portrait_script)
        self.assertIn("profile.fps", portrait_script)
        self.assertIn("maxNodes: lite ? 520 : 980", portrait_script)
        self.assertIn('type === "face-surface"', graph_generator)
        self.assertIn("const buckets = new Map()", graph_generator)
        self.assertIn("bucketSize = connectionDistance", graph_generator)
        self.assertIn("refreshColors", graph_renderer)
        self.assertIn("faceSurface", graph_renderer)
        self.assertIn("enhanceEdgesWithOpenCV", image_sampler)
        self.assertIn("blendEdges", image_sampler)
        self.assertIn("cv.Canny", opencv_enhancer)
        self.assertIn("source.delete()", opencv_enhancer)

    def test_github_is_visible_and_cv_action_is_removed(self):
        response = self.client.get("/")
        bubbles = json.loads(response.context["bubbles_json"])
        contact = next(node for node in bubbles if node["id"] == "contact")
        labels = [child["label"] for child in contact["children"]]

        self.assertContains(response, "https://github.com/sebastian123431")
        self.assertIn("GitHub", labels)
        self.assertNotIn("Descargar CV", labels)
        self.assertNotContains(response, "Descargar CV")

    def test_profile_panel_links_to_bibliography(self):
        response = self.client.get("/")
        bubbles = json.loads(response.context["bubbles_json"])
        profile = next(node for node in bubbles if node["id"] == "profile")

        self.assertIn("actions", profile)
        self.assertEqual(profile["actions"][0]["href"], "/bibliografia/")
        self.assertIn("bibliograf", profile["actions"][0]["label"].lower())

    def test_bibliography_portrait_uses_versioned_static_url(self):
        response = self.client.get("/bibliografia/")

        self.assertEqual(response.status_code, 200)
        self.assertIn("portrait_src", response.context)
        self.assertIn("/static/portafoliosapp/images/portrait/yo.png?v=", response.context["portrait_src"])
        self.assertIn("/static/portafoliosapp/DigitalPortrait/DigitalPortrait.css?v=", response.context["bio_css_src"])
        self.assertIn("/static/portafoliosapp/DigitalPortrait/DigitalPortrait.js?v=", response.context["bio_js_src"])
        self.assertContains(response, "https://docs.opencv.org/4.12.0/opencv.js")
        self.assertContains(response, "window.__opencvReady")

    def test_bibliography_is_single_cover_layout(self):
        response = self.client.get("/bibliografia/")
        base_dir = Path(__file__).resolve().parents[1]
        styles = (base_dir / "static" / "portafoliosapp" / "DigitalPortrait" / "DigitalPortrait.css").read_text(encoding="utf-8")

        self.assertContains(response, 'class="bio-summary"')
        self.assertNotContains(response, 'class="bio-content"')
        self.assertIn("overflow: hidden", styles[styles.find("body {"):styles.find("body,")])
        self.assertIn("min-height: 100dvh", styles)

class PortfolioV5InteractionTests(TestCase):
    def test_home_uses_scroll_to_accordion_experience(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="graph-stage"')
        self.assertContains(response, 'id="node-rail"')
        self.assertContains(response, 'id="module-stack"')
        self.assertContains(response, 'data-expand-all')
        self.assertContains(response, 'data-collapse-all')
        self.assertContains(response, "portfolio-v5.css")
        self.assertContains(response, "portfolio-v5.js")

    def test_v5_keeps_independent_expandable_modules_and_scroll_morph(self):
        base_dir = Path(__file__).resolve().parents[1]
        script = (base_dir / "static" / "portafoliosapp" / "js" / "portfolio-v5.js").read_text(encoding="utf-8")
        self.assertIn('document.createElement("details")', script)
        self.assertIn("function setModuleOpen", script)
        self.assertIn("function updateScrollMorph", script)
        self.assertIn("card.open = Boolean(open)", script)
        self.assertNotIn("closeOtherModules", script)

    def test_v5_preserves_contact_evidence_and_route_interactions(self):
        base_dir = Path(__file__).resolve().parents[1]
        script = (base_dir / "static" / "portafoliosapp" / "js" / "portfolio-v5.js").read_text(encoding="utf-8")
        self.assertIn("data-reveal-contact", script)
        self.assertIn("/api/reveal-contact/", script)
        self.assertIn("data-media-src", script)
        self.assertIn("navigator.geolocation.getCurrentPosition", script)

    def test_v5_mobile_turns_left_rail_into_sticky_horizontal_navigation(self):
        base_dir = Path(__file__).resolve().parents[1]
        styles = (base_dir / "static" / "portafoliosapp" / "css" / "portfolio-v5.css").read_text(encoding="utf-8")
        mobile = styles[styles.find("@media (max-width: 880px)"):styles.find("@media (max-width: 620px)")]
        self.assertIn(".node-rail-shell { position:sticky", mobile)
        self.assertIn("overflow-x:auto", mobile)
        self.assertIn(".node-rail { display:flex", mobile)
