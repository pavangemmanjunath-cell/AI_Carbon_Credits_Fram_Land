/** Strings for the "Locked land" card, registered under `lockedLand.*` in all six app languages. */
import i18n from '@/i18n';

const en = {
  title: 'Locked land: coordinates and trees',
  subtitle:
    'Your saved boundary. Coordinates stay on this screen and are never sent to an AI model.',
  area: 'Area',
  perimeter: 'Perimeter',
  corners: 'Corners',
  lat: 'Latitude',
  lon: 'Longitude',
  copy: 'Copy coordinates',
  copied: 'Copied',
  species: 'Species to plant',
  fit: '{{count}} trees fit at about {{spacing}} m × {{spacing}} m spacing',
  fitSource: 'Reference density {{density}} per ha — {{source}} ({{status}})',
  noDensity: 'This species has no configured planting density, so no tree count is given.',
  capped: 'The simulation handles up to 2,000 trees; it will open with 2,000.',
  simulate: 'Simulate this land',
};
type Bundle = typeof en;

const hi: Bundle = {
  title: 'लॉक की गई ज़मीन: निर्देशांक और पेड़',
  subtitle:
    'आपकी सहेजी गई सीमा। निर्देशांक इसी स्क्रीन पर रहते हैं और किसी एआई मॉडल को नहीं भेजे जाते।',
  area: 'क्षेत्रफल',
  perimeter: 'परिधि',
  corners: 'कोने',
  lat: 'अक्षांश',
  lon: 'देशांतर',
  copy: 'निर्देशांक कॉपी करें',
  copied: 'कॉपी हो गया',
  species: 'लगाने के लिए प्रजाति',
  fit: 'लगभग {{spacing}} मी × {{spacing}} मी दूरी पर {{count}} पेड़ आ सकते हैं',
  fitSource: 'संदर्भ घनत्व {{density}} प्रति हेक्टेयर — {{source}} ({{status}})',
  noDensity: 'इस प्रजाति का रोपण घनत्व कॉन्फ़िग में नहीं है, इसलिए पेड़ों की संख्या नहीं दी गई।',
  capped: 'सिमुलेशन 2,000 पेड़ों तक चलता है; यह 2,000 के साथ खुलेगा।',
  simulate: 'इस ज़मीन का सिमुलेशन करें',
};
const kn: Bundle = {
  title: 'ಲಾಕ್ ಮಾಡಿದ ಭೂಮಿ: ನಿರ್ದೇಶಾಂಕಗಳು ಮತ್ತು ಮರಗಳು',
  subtitle:
    'ನಿಮ್ಮ ಉಳಿಸಿದ ಗಡಿ. ನಿರ್ದೇಶಾಂಕಗಳು ಈ ಪರದೆಯಲ್ಲೇ ಇರುತ್ತವೆ ಮತ್ತು ಯಾವುದೇ ಎಐ ಮಾದರಿಗೆ ಕಳುಹಿಸುವುದಿಲ್ಲ.',
  area: 'ವಿಸ್ತೀರ್ಣ',
  perimeter: 'ಸುತ್ತಳತೆ',
  corners: 'ಮೂಲೆಗಳು',
  lat: 'ಅಕ್ಷಾಂಶ',
  lon: 'ರೇಖಾಂಶ',
  copy: 'ನಿರ್ದೇಶಾಂಕಗಳನ್ನು ನಕಲಿಸಿ',
  copied: 'ನಕಲಿಸಲಾಗಿದೆ',
  species: 'ನೆಡಬೇಕಾದ ಜಾತಿ',
  fit: 'ಸುಮಾರು {{spacing}} ಮೀ × {{spacing}} ಮೀ ಅಂತರದಲ್ಲಿ {{count}} ಮರಗಳು ಹಿಡಿಸುತ್ತವೆ',
  fitSource: 'ಉಲ್ಲೇಖ ಸಾಂದ್ರತೆ ಹೆಕ್ಟೇರ್‌ಗೆ {{density}} — {{source}} ({{status}})',
  noDensity: 'ಈ ಜಾತಿಗೆ ನೆಡುವ ಸಾಂದ್ರತೆ ಸಂರಚಿಸಿಲ್ಲ, ಆದ್ದರಿಂದ ಮರಗಳ ಸಂಖ್ಯೆ ನೀಡಿಲ್ಲ.',
  capped: 'ಸಿಮ್ಯುಲೇಶನ್ 2,000 ಮರಗಳವರೆಗೆ ನಡೆಯುತ್ತದೆ; ಇದು 2,000 ರೊಂದಿಗೆ ತೆರೆಯುತ್ತದೆ.',
  simulate: 'ಈ ಭೂಮಿಯನ್ನು ಸಿಮ್ಯುಲೇಟ್ ಮಾಡಿ',
};
const de: Bundle = {
  title: 'Fixierte Fläche: Koordinaten und Bäume',
  subtitle:
    'Ihre gespeicherte Grenze. Koordinaten bleiben auf diesem Bildschirm und gehen nie an ein KI-Modell.',
  area: 'Fläche',
  perimeter: 'Umfang',
  corners: 'Eckpunkte',
  lat: 'Breite',
  lon: 'Länge',
  copy: 'Koordinaten kopieren',
  copied: 'Kopiert',
  species: 'Zu pflanzende Art',
  fit: '{{count}} Bäume passen bei etwa {{spacing}} m × {{spacing}} m Abstand',
  fitSource: 'Referenzdichte {{density}} je ha — {{source}} ({{status}})',
  noDensity: 'Für diese Art ist keine Pflanzdichte konfiguriert, daher keine Baumzahl.',
  capped: 'Die Simulation rechnet mit bis zu 2.000 Bäumen; sie öffnet mit 2.000.',
  simulate: 'Diese Fläche simulieren',
};
const fr: Bundle = {
  title: 'Terrain verrouillé : coordonnées et arbres',
  subtitle:
    'Votre limite enregistrée. Les coordonnées restent sur cet écran et ne sont jamais envoyées à un modèle d’IA.',
  area: 'Surface',
  perimeter: 'Périmètre',
  corners: 'Sommets',
  lat: 'Latitude',
  lon: 'Longitude',
  copy: 'Copier les coordonnées',
  copied: 'Copié',
  species: 'Espèce à planter',
  fit: '{{count}} arbres tiennent avec un espacement d’environ {{spacing}} m × {{spacing}} m',
  fitSource: 'Densité de référence {{density}} par ha — {{source}} ({{status}})',
  noDensity:
    'Aucune densité de plantation n’est configurée pour cette espèce : pas de nombre d’arbres.',
  capped: 'La simulation va jusqu’à 2 000 arbres ; elle s’ouvrira avec 2 000.',
  simulate: 'Simuler ce terrain',
};
const es: Bundle = {
  title: 'Terreno bloqueado: coordenadas y árboles',
  subtitle:
    'Su límite guardado. Las coordenadas se quedan en esta pantalla y nunca se envían a un modelo de IA.',
  area: 'Superficie',
  perimeter: 'Perímetro',
  corners: 'Vértices',
  lat: 'Latitud',
  lon: 'Longitud',
  copy: 'Copiar coordenadas',
  copied: 'Copiado',
  species: 'Especie a plantar',
  fit: 'Caben {{count}} árboles con un espaciado de unos {{spacing}} m × {{spacing}} m',
  fitSource: 'Densidad de referencia {{density}} por ha — {{source}} ({{status}})',
  noDensity:
    'Esta especie no tiene densidad de plantación configurada, así que no se da un número de árboles.',
  capped: 'La simulación admite hasta 2.000 árboles; se abrirá con 2.000.',
  simulate: 'Simular este terreno',
};

export const lockedLandBundles = { en, hi, kn, de, fr, es };
for (const [language, lockedLand] of Object.entries(lockedLandBundles)) {
  i18n.addResourceBundle(language, 'translation', { lockedLand }, true, false);
}
