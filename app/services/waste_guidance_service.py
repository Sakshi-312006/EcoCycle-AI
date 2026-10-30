"""Pillar 1 & Pillar 5: Specific Waste Handling Guidance and Decision Engine.

Provides evidence-based scientific composting advice, hygiene precautions, and verified
authoritative statutory citations (MoEFCC SWM Rules 2016, BMWM Rules 2016) with explicit,
testable action outcomes:
- HOME_HANDLING_RECOMMENDED: citizen composts/processes on-site; ordinary pickup disabled.
- COLLECTION_APPROPRIATE: recyclable/sanitary waste; citizen may choose to request pickup.
- SPECIAL_HANDLING_REQUIRED: hazardous or infectious biomedical waste; ordinary doorstep pickup blocked.
- UNCERTAIN_CONFIRMATION_REQUIRED: ambiguous or unverified contamination status requiring citizen confirmation.

Supports all 6 regional languages (EN, HI, KN, TA, TE, MR).
"""

from typing import Any, Dict, List, Optional
from app.schemas.voice import LanguageCodeEnum
from app.schemas.waste import WasteStreamEnum
from app.schemas.waste_workflow import (
    ActionOutcomeEnum,
    HandlingGuidanceRequest,
    HandlingGuidanceResponse,
)
from app.services.voice_service import LOCALIZED_INSTRUCTIONS, VoiceService

# Authoritative Gazette and Rule Constants
SOURCE_SWM_2016 = "MoEFCC Solid Waste Management Rules, 2016 (Notification S.O. 1357(E), 8 April 2016)"
SOURCE_BMWM_2016 = "MoEFCC Bio-Medical Waste Management Rules, 2016 (Notification G.S.R. 343(E), 28 March 2016, as amended)"
URL_CPCB_SWM = "https://cpcb.nic.in/waste-management-rules/"
URL_CPCB_BMWM = "https://cpcb.nic.in/bio-medical-waste-rules/"
VERIFICATION_DATE = "2026-10-29"

# Verified Evidence-Based Knowledge Base
ITEM_GUIDANCE_DB: Dict[str, Dict[str, Any]] = {
    "raw_fruit_scraps": {
        "category": WasteStreamEnum.WET_ORGANIC,
        "item_or_stream": "raw_fruit_scraps",
        "scientific_guidance": (
            "Raw fruit and vegetable peelings are high-nitrogen, moisture-rich organic 'greens'. "
            "They are well-suited for decentralized aerobic home composting (backyard compost piles, terracotta Khamba pots, "
            "or pit composting). In composting science (CPCB MSW Composting Guidelines & Cornell Composting), an initial Carbon-to-Nitrogen (C:N) "
            "ratio of 25:1 to 30:1 is recommended for rapid, odor-free decomposition. Because dry leaves and shredded plain paper ('browns') "
            "have low bulk density, household composting manuals practically approximate this balance as a 2:1 to 3:1 volume ratio "
            "(2 to 3 parts loose dry carbonaceous material to 1 part moist fresh kitchen waste). Aerating the pile once weekly maintains aerobic conditions and prevents foul anaerobic odors."
        ),
        "safety_precautions": "Keep compost vessels covered with a breathable lid or fine mesh to prevent fruit fly (Drosophila) breeding.",
        "statutory_guidance": (
            "Under Solid Waste Management Rules, 2016, Rule 4(1)(a) & Rule 4(2), generators are legally mandated to segregate "
            "biodegradable waste at source and are explicitly encouraged to practice on-site composting or bio-methanation where space permits."
        ),
        "statutory_reference": "MoEFCC Solid Waste Management Rules, 2016, Rule 4(1)(a)",
        "statutory_requirement": "Segregate bio-degradable waste at source. Facilitate composting or bio-methanation on-site where feasible.",
        "official_source_title": SOURCE_SWM_2016,
        "official_source_url": URL_CPCB_SWM,
        "rule_or_schedule_reference": "Rule 4(1)(a) & Rule 4(2)",
        "verification_date": VERIFICATION_DATE,
        "home_handling_suitable": True,
        "default_outcome": ActionOutcomeEnum.HOME_HANDLING_RECOMMENDED,
        "pickup_available": False,
        "ordinary_pickup_allowed": False,
        "specialized_disposal_required": False,
        "requires_human_review": False,
        "localized": {
            "hi": {
                "title": "सब्जी और फलों के छिलके - घर पर खाद बनाएं",
                "action_message": "घर पर खाद बनाना सबसे उत्तम है। किसी संग्रह या पिकअप की आवश्यकता नहीं है।",
            },
            "kn": {
                "title": "ಹಣ್ಣು ಮತ್ತು ತರಕಾರಿ ತ್ಯಾಜ್ಯ - ಮನೆಯಲ್ಲೇ ಗೊಬ್ಬರ ಮಾಡಿ",
                "action_message": "ಮನೆಯಲ್ಲೇ ಕಾಂಪೋಸ್ಟ್ ಮಾಡುವುದು ಉತ್ತಮ. ಡೋರ್‌ಸ್ಟೆಪ್ ಪಿಕಪ್ ಅಗತ್ಯವಿಲ್ಲ.",
            },
            "ta": {
                "title": "பழம் மற்றும் காய்கறி கழிவுகள் - வீட்டிலேயே உரம் தயாரிக்கவும்",
                "action_message": "வீட்டு உரமாக்கல் பரிந்துரைக்கப்படுகிறது. பிக்கப் தேவையில்லை.",
            },
            "te": {
                "title": "పండ్లు మరియు కూరగాయల వ్యర్థాలు - ఇంట్లోనే కంపోస్ట్ చేయండి",
                "action_message": "ఇంట్లోనే కంపోస్ట్ చేయడం ఉత్తమం. పికప్ అభ్యర్థన అవసరం లేదు.",
            },
            "mr": {
                "title": "फळे आणि भाज्यांचे अवशेष - घरीच खत बनवा",
                "action_message": "घरच्या घरी खत निर्मिती सर्वोत्तम पर्याय आहे. पिकअपची आवश्यकता नाही.",
            },
        },
    },
    "citrus_chilli_scraps": {
        "category": WasteStreamEnum.WET_ORGANIC,
        "item_or_stream": "citrus_chilli_scraps",
        "scientific_guidance": (
            "Citrus rinds contain citric acid and volatile d-limonene, while hot chillies contain capsaicin. "
            "In conventional hot aerobic backyard composting or pit composting, both decompose readily without inhibition when mixed "
            "with balanced organic matter. In vermicomposting (earthworm culture bins), however, earthworms (Eisenia fetida) breathe through "
            "their moist skin and thrive in near-neutral pH (6.5–8.0); large, concentrated additions of acidic citrus or capsaicin can alter bedding pH "
            "and irritate worm dermal surfaces. Small, well-diluted amounts added to substantial neutral bedding are safely broken down. "
            "Universal prohibitions against composting citrus or chillies are scientifically unfounded."
        ),
        "safety_precautions": "Avoid direct eye contact after handling hot chilli seeds; wash hands thoroughly.",
        "statutory_guidance": "Classified as bio-degradable waste under SWM Rules, 2016, Rule 4(1)(a). Decentralized source composting is encouraged.",
        "statutory_reference": "MoEFCC Solid Waste Management Rules, 2016, Rule 4(1)(a)",
        "statutory_requirement": "Segregate bio-degradable waste at source.",
        "official_source_title": SOURCE_SWM_2016,
        "official_source_url": URL_CPCB_SWM,
        "rule_or_schedule_reference": "Rule 4(1)(a)",
        "verification_date": VERIFICATION_DATE,
        "home_handling_suitable": True,
        "default_outcome": ActionOutcomeEnum.HOME_HANDLING_RECOMMENDED,
        "pickup_available": False,
        "ordinary_pickup_allowed": False,
        "specialized_disposal_required": False,
        "requires_human_review": False,
        "localized": {
            "hi": {
                "title": "नींबू के छिलके और मिर्च - घर पर खाद प्रबंधन",
                "action_message": "सामान्य खाद के लिए उपयुक्त; केंचुआ खाद में केवल संतुलित मात्रा डालें। पिकअप आवश्यक नहीं।",
            },
            "kn": {
                "title": "ನಿಂಬೆ ಸಿಪ್ಪೆ ಮತ್ತು ಮೆಣಸಿನಕಾಯಿ - ಮನೆಯಲ್ಲೇ ನಿರ್ವಹಣೆ",
                "action_message": "ಸಾಮಾನ್ಯ ಕಾಂಪೋಸ್ಟ್‌ಗೆ ಸೂಕ್ತ; ಎರೆಹುಳು ಗೊಬ್ಬರಕ್ಕೆ ಹೆಚ್ಚಿನ ಪ್ರಮಾಣ ಹಾಕಬೇಡಿ.",
            },
        },
    },
    "used_diapers": {
        "category": WasteStreamEnum.SANITARY,
        "item_or_stream": "used_diapers",
        "scientific_guidance": (
            "Disposable baby and adult diapers are engineered with polypropylene/polyethylene non-woven barrier films, "
            "sodium polyacrylate superabsorbent polymer (SAP) absorbent cores, and human biological waste containing potential enteric pathogens. "
            "They are completely non-biodegradable and unsuitable for home composting. Flushing into plumbing causes severe sewer clogging."
        ),
        "safety_precautions": (
            "Fold the diaper inward to securely encapsulate fecal waste. Wrap tightly in newspaper or opaque disposal pouches "
            "to prevent pathogen exposure and odor prior to sanitation collection."
        ),
        "statutory_guidance": (
            "Under Solid Waste Management Rules, 2016, Rule 4(1)(b), waste generators shall wrap securely the used sanitary waste "
            "like diapers, sanitary pads etc., in the pouches provided by the manufacturers or brand owners of these products "
            "or in a suitable wrapping material as instructed by the local authorities and place the same in the non-biodegradable waste bin. "
            "Note: Specific symbol markings are local municipal advisories where stipulated, not a national statutory mandate."
        ),
        "statutory_reference": "MoEFCC Solid Waste Management Rules, 2016, Rule 4(1)(b)",
        "statutory_requirement": (
            "Wrap securely used sanitary waste in manufacturer-supplied pouches or suitable wrapping material as instructed by local authorities."
        ),
        "official_source_title": SOURCE_SWM_2016,
        "official_source_url": URL_CPCB_SWM,
        "rule_or_schedule_reference": "Rule 4(1)(b)",
        "verification_date": VERIFICATION_DATE,
        "home_handling_suitable": False,
        "default_outcome": ActionOutcomeEnum.COLLECTION_APPROPRIATE,
        "pickup_available": True,
        "ordinary_pickup_allowed": True,
        "specialized_disposal_required": False,
        "requires_human_review": False,
        "localized": {
            "hi": {
                "title": "इस्तेमाल किया हुआ डायपर - सैनिटरी कचरा संग्रहण",
                "action_message": "कागज या पाउच में अच्छी तरह लपेटकर सैनिटरी कचरा संग्रह हेतु दें। पिकअप उपलब्ध है।",
            },
            "kn": {
                "title": "ಬಳಸಿದ ಡೈಪರ್ - ಸ್ಯಾನಿಟರಿ ತ್ಯಾಜ್ಯ ಸಂಗ್ರಹ",
                "action_message": "ಸುರಕ್ಷಿತವಾಗಿ ಕಾಗದದಲ್ಲಿ ಸುತ್ತಿ ಸ್ಯಾನಿಟರಿ ತ್ಯಾಜ್ಯವಾಗಿ ನೀಡಿ. ಪಿಕಪ್ ಲಭ್ಯವಿದೆ.",
            },
        },
    },
    "medical_bandages": {
        "category": WasteStreamEnum.SANITARY,
        "item_or_stream": "medical_bandages",
        "scientific_guidance": (
            "Wound dressings and bandages present divergent biological risks depending on bodily fluid exposure. "
            "Minor household adhesive bandages (band-aids) with negligible contamination carry minimal risk and can be wrapped as domestic waste. "
            "Conversely, dressings soaked with blood, purulent discharge, or originating from communicable medical care carry potential "
            "blood-borne pathogens (Hepatitis B, HIV, MRSA) and must NEVER be mixed into ordinary municipal collection."
        ),
        "safety_precautions": (
            "Wear protective gloves when handling contaminated dressings. If blood-soaked, place immediately into a leak-proof container "
            "or yellow non-chlorinated plastic biohazard bag. Keep isolated from domestic waste."
        ),
        "statutory_guidance": (
            "Soiled medical dressings contaminated with blood or body fluids are classified under Schedule I, Part-1 (Yellow Category) "
            "of the Bio-Medical Waste Management Rules, 2016. Furthermore, SWM Rules 2016 Rule 2 explicitly excludes bio-medical waste, "
            "and Rule 3(1)(17) classifies household contaminated gauge and needles as Domestic Hazardous Waste. Contaminated dressings must be "
            "transferred to an authorized Common Bio-medical Waste Treatment Facility (CBWTF) for high-temperature incineration or autoclaving. "
            "Disposal into ordinary municipal collection is prohibited."
        ),
        "statutory_reference": "MoEFCC Bio-Medical Waste Management Rules, 2016 (Schedule I, Yellow Category) & SWM Rules 2016, Rule 3(1)(17)",
        "statutory_requirement": (
            "Segregate soiled bio-medical waste in yellow non-chlorinated containers for treatment at an authorized CBWTF. Do not mix into municipal solid waste."
        ),
        "official_source_title": SOURCE_BMWM_2016,
        "official_source_url": URL_CPCB_BMWM,
        "rule_or_schedule_reference": "BMWM Rules 2016 Schedule I (Yellow Category) & SWM Rules 2016 Rule 3(1)(17)",
        "verification_date": VERIFICATION_DATE,
        "home_handling_suitable": False,
        "default_outcome": ActionOutcomeEnum.SPECIAL_HANDLING_REQUIRED,
        "pickup_available": False,
        "ordinary_pickup_allowed": False,
        "specialized_disposal_required": True,
        "requires_human_review": True,
        "localized": {
            "hi": {
                "title": "चिकित्सा पट्टी / ड्रेसिंग - बायोमेडिकल वेस्ट चेतावनी",
                "action_message": "रक्त या मवाद से दूषित पट्टियों को सामान्य कचरे में न डालें। अधिकृत CBWTF केंद्र या अस्पताल में सौंपें।",
            },
            "kn": {
                "title": "ವೈದ್ಯಕೀಯ ಬ್ಯಾಂಡೇಜ್ - ಜೈವಿಕ ವೈದ್ಯಕೀಯ ತ್ಯಾಜ್ಯ ಎಚ್ಚರಿಕೆ",
                "action_message": "ರಕ್ತ ಅಥವಾ ಸೋಂಕು ತಗುಲಿದ ಬ್ಯಾಂಡೇಜ್‌ಗಳನ್ನು ಸಾಮಾನ್ಯ ಪಿಕಪ್‌ನಲ್ಲಿ ನೀಡಬೇಡಿ. ಅಧಿಕೃತ CBWTF ಕೇಂದ್ರಕ್ಕೆ ನೀಡಿ.",
            },
        },
    },
}


class WasteGuidanceService:
    """Service generating verified statutory citations, scientific guidance, and explicit action decisions."""

    @classmethod
    def get_guidance(cls, request: HandlingGuidanceRequest) -> HandlingGuidanceResponse:
        """Resolve specific handling instructions and testable action outcome."""
        cat = request.category
        item_key = (request.item or "").lower().strip()
        lang_code = request.language.value

        # 1. Check if item is known specific item
        item_data = ITEM_GUIDANCE_DB.get(item_key)

        # 2. Case D Special Distinction: Medical bandages (Infectious vs Minor Household)
        if item_key == "medical_bandages":
            if request.is_potentially_infectious:
                # Potentially infectious / blood-contaminated dressing
                scientific = item_data["scientific_guidance"]
                safety = item_data["safety_precautions"]
                statutory = item_data["statutory_guidance"]
                stat_ref = item_data["statutory_reference"]
                stat_req = item_data["statutory_requirement"]
                source_title = item_data["official_source_title"]
                source_url = item_data["official_source_url"]
                rule_ref = item_data["rule_or_schedule_reference"]
                home_suitable = False
                collection_rec = False
                pickup_avail = False
                ord_pickup = False
                specialized = True
                human_review = False
                outcome = ActionOutcomeEnum.SPECIAL_HANDLING_REQUIRED
                action_msg = (
                    "Potentially infectious biomedical material. Ordinary municipal doorstep pickup is prohibited. "
                    "Hand over in yellow biohazard container to an authorized healthcare facility or CBWTF."
                )
                actions = ["find_authorized_cbwtf", "view_safety_protocol", "exit_to_home"]
                title = "Infectious Medical Dressing (Bio-Medical Waste)"

            elif request.is_potentially_infectious is False and request.item == "medical_bandages" and not request.is_potentially_infectious:
                # Explicitly declared as minor non-infectious household adhesive bandage
                scientific = (
                    "Minor domestic adhesive bandages (band-aids with negligible non-infectious fluid) carry minimal pathogen risk. "
                    "Wrap securely in a paper pouch and deposit in the household sanitary/non-biodegradable waste stream."
                )
                safety = "Ensure adhesive strip is folded inward and wrapped securely in paper before disposal."
                statutory = (
                    "Under Solid Waste Management Rules, 2016, Rule 4(1)(b), household non-biodegradable sanitary waste "
                    "shall be securely wrapped in suitable wrapping material and handed to the waste collector."
                )
                stat_ref = "MoEFCC Solid Waste Management Rules, 2016, Rule 4(1)(b)"
                stat_req = "Wrap securely in paper or pouches as instructed by local authority."
                source_title = SOURCE_SWM_2016
                source_url = URL_CPCB_SWM
                rule_ref = "Rule 4(1)(b)"
                home_suitable = False
                collection_rec = True
                pickup_avail = True
                ord_pickup = True
                specialized = False
                human_review = False
                outcome = ActionOutcomeEnum.COLLECTION_APPROPRIATE
                action_msg = "Wrap securely in paper and request scheduled sanitary doorstep collection."
                actions = ["request_pickup", "exit_to_home", "change_category"]
                title = "Minor Household Bandage (Domestic Sanitary)"

            else:
                # Ambiguous contamination status: require explicit clarification before routing
                scientific = "Medical bandages must be triaged based on presence of blood, pus, or infectious contaminants."
                safety = "Do not handle barehanded if contaminated with bodily fluids."
                statutory = "Bio-medical waste must not be mixed with municipal solid waste as per BMWM Rules 2016."
                stat_ref = SOURCE_BMWM_2016
                stat_req = "Confirm contamination status before disposal routing."
                source_title = SOURCE_BMWM_2016
                source_url = URL_CPCB_BMWM
                rule_ref = "Schedule I (Yellow Category)"
                home_suitable = False
                collection_rec = False
                pickup_avail = False
                ord_pickup = False
                specialized = True
                human_review = True
                outcome = ActionOutcomeEnum.UNCERTAIN_CONFIRMATION_REQUIRED
                action_msg = "Please confirm whether this dressing is contaminated with blood or bodily fluids."
                actions = ["confirm_contamination_status", "exit_to_home"]
                title = "Medical Bandage Contamination Review"

        elif item_data:
            # Verified specific item
            scientific = item_data["scientific_guidance"]
            safety = item_data["safety_precautions"]
            statutory = item_data["statutory_guidance"]
            stat_ref = item_data["statutory_reference"]
            stat_req = item_data.get("statutory_requirement")
            source_title = item_data.get("official_source_title")
            source_url = item_data.get("official_source_url")
            rule_ref = item_data.get("rule_or_schedule_reference")
            home_suitable = item_data["home_handling_suitable"]
            outcome = item_data["default_outcome"]
            pickup_avail = item_data["pickup_available"]
            ord_pickup = item_data.get("ordinary_pickup_allowed", pickup_avail)
            specialized = item_data.get("specialized_disposal_required", False)
            human_review = item_data.get("requires_human_review", False)
            collection_rec = not home_suitable

            title = f"{item_key.replace('_', ' ').title()} Handling Guidance"
            action_msg = (
                "Home composting is recommended. No collection is required."
                if outcome == ActionOutcomeEnum.HOME_HANDLING_RECOMMENDED
                else (
                    "Potentially hazardous or infectious material. Ordinary municipal doorstep pickup is prohibited."
                    if outcome == ActionOutcomeEnum.SPECIAL_HANDLING_REQUIRED
                    else "Sanitary collection is recommended. Doorstep pickup is available."
                )
            )

            actions = (
                ["exit_to_home", "view_composting_guide", "change_category"]
                if outcome == ActionOutcomeEnum.HOME_HANDLING_RECOMMENDED
                else (
                    ["find_authorized_facility", "view_safety_protocol", "exit_to_home"]
                    if outcome == ActionOutcomeEnum.SPECIAL_HANDLING_REQUIRED
                    else ["request_pickup", "exit_to_home", "change_category"]
                )
            )

            # Check localized overrides
            loc = item_data.get("localized", {}).get(lang_code)
            if loc:
                title = loc.get("title", title)
                action_msg = loc.get("action_message", action_msg)

        else:
            # Generic 4-stream fallback
            generic_instructions = LOCALIZED_INSTRUCTIONS.get(lang_code, LOCALIZED_INSTRUCTIONS["en"])
            stream_meta = generic_instructions["streams"].get(cat.value)
            source_title = SOURCE_SWM_2016
            source_url = URL_CPCB_SWM

            if cat == WasteStreamEnum.WET_ORGANIC:
                if request.has_home_composting_setup:
                    home_suitable = True
                    collection_rec = False
                    pickup_avail = False
                    ord_pickup = False
                    outcome = ActionOutcomeEnum.HOME_HANDLING_RECOMMENDED
                    action_msg = "Home composting setup active. Please process in your home compost unit."
                    actions = ["exit_to_home", "view_composting_guide", "change_category"]
                else:
                    home_suitable = False
                    collection_rec = True
                    pickup_avail = True
                    ord_pickup = True
                    outcome = ActionOutcomeEnum.COLLECTION_APPROPRIATE
                    action_msg = "Wet organic collection scheduled for morning rounds. Doorstep pickup available."
                    actions = ["request_pickup", "exit_to_home", "change_category"]

                scientific = "Biodegradable organic kitchen waste decomposes aerobically into nutrient-rich compost."
                safety = "Keep unbagged or in certified compostable bin liners to prevent leachate."
                statutory = "Under SWM Rules 2016 Rule 4(1)(a), generators must segregate biodegradable waste at source."
                stat_ref = "MoEFCC SWM Rules, 2016, Rule 4(1)(a)"
                stat_req = "Segregate biodegradable waste into green stream."
                rule_ref = "Rule 4(1)(a)"
                specialized = False
                human_review = False
                title = f"{stream_meta.stream_name_localized if stream_meta else 'Wet Organic'} Guidance"

            elif cat == WasteStreamEnum.DRY_RECYCLABLE:
                home_suitable = False
                collection_rec = True
                pickup_avail = True
                ord_pickup = True
                specialized = False
                human_review = False
                outcome = ActionOutcomeEnum.COLLECTION_APPROPRIATE
                action_msg = "Dry recyclables should be cleaned, kept dry, and handed over for material recovery."
                actions = ["request_pickup", "exit_to_home", "change_category"]
                scientific = "Clean paper, cardboard, PET/HDPE plastics, and metals preserve maximum circular value when dry."
                safety = "Ensure glass bottles are unbroken; rinse food containers to prevent mold."
                statutory = "SWM Rules 2016 Rule 4(1)(a) mandates handing over clean dry recyclables to authorized collectors."
                stat_ref = "MoEFCC SWM Rules, 2016, Rule 4(1)(a)"
                stat_req = "Segregate dry recyclables into blue stream."
                rule_ref = "Rule 4(1)(a)"
                title = f"{stream_meta.stream_name_localized if stream_meta else 'Dry Recyclable'} Guidance"

            elif cat == WasteStreamEnum.SANITARY:
                home_suitable = False
                collection_rec = True
                pickup_avail = True
                ord_pickup = True
                specialized = False
                human_review = False
                outcome = ActionOutcomeEnum.COLLECTION_APPROPRIATE
                action_msg = "Wrap securely in paper or pouches before handover. Doorstep pickup is available."
                actions = ["request_pickup", "exit_to_home", "change_category"]
                scientific = "Sanitary waste includes non-infectious hygiene items requiring secure physical wrapping."
                safety = "Wrap securely to protect collection staff; never flush down toilets."
                statutory = "SWM Rules 2016 Rule 4(1)(b) mandates separate secure wrapping for sanitary items."
                stat_ref = "MoEFCC SWM Rules, 2016, Rule 4(1)(b)"
                stat_req = "Wrap sanitary waste securely before placing in dry/non-biodegradable collection."
                rule_ref = "Rule 4(1)(b)"
                title = f"{stream_meta.stream_name_localized if stream_meta else 'Sanitary'} Guidance"

            else:  # HAZARDOUS
                home_suitable = False
                collection_rec = False
                pickup_avail = False
                ord_pickup = False
                specialized = True
                human_review = False
                outcome = ActionOutcomeEnum.SPECIAL_HANDLING_REQUIRED
                action_msg = (
                    "Domestic hazardous waste (batteries, CFL bulbs, chemicals) must not be mixed into ordinary collection. "
                    "Deposit at a designated municipal hazardous drop-off kiosk."
                )
                actions = ["find_hazardous_kiosk", "view_safety_protocol", "exit_to_home"]
                scientific = "Heavy metals (lead, mercury, cadmium) and toxic chemicals contaminate compost and groundwater."
                safety = "Handle with care; do not puncture batteries or break fluorescent tube lights."
                statutory = "SWM Rules 2016 Rule 3(1)(17) & Rule 4(1)(a) mandate separate storage of domestic hazardous waste."
                stat_ref = "MoEFCC SWM Rules, 2016, Rule 3(1)(17) & Rule 4(1)(a)"
                stat_req = "Store domestic hazardous waste separately and deposit at designated drop-off centers."
                rule_ref = "Rule 3(1)(17) & Rule 4(1)(a)"
                title = f"{stream_meta.stream_name_localized if stream_meta else 'Domestic Hazardous'} Warning"

        return HandlingGuidanceResponse(
            category=cat,
            item=item_key if item_key else None,
            item_or_stream=item_key if item_key else cat.value,
            language=lang_code,
            title=title,
            scientific_guidance=scientific,
            safety_precautions=safety,
            statutory_guidance=statutory,
            statutory_reference=stat_ref,
            statutory_requirement=stat_req,
            official_source_title=source_title,
            official_source_url=source_url,
            rule_or_schedule_reference=rule_ref,
            verification_date=VERIFICATION_DATE,
            home_handling_suitable=home_suitable,
            collection_recommended=collection_rec,
            pickup_available=pickup_avail,
            ordinary_pickup_allowed=ord_pickup,
            specialized_disposal_required=specialized,
            requires_human_review=human_review,
            action_outcome=outcome,
            action_message=action_msg,
            allowed_next_actions=actions,
        )
