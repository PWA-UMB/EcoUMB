"""Contenido educativo fijo: la norma y las buenas prácticas (RF-27, RF-28)."""

from app.domain.entities.education import Normative, Practice

NORMATIVE = Normative(
    title="Código de colores — Resolución 2184 de 2019",
    summary=(
        "En Colombia los residuos se separan en la fuente con un código de colores único: bolsa "
        "blanca para los residuos aprovechables (plástico, vidrio, metales, papel y cartón), "
        "bolsa negra para los no aprovechables y bolsa verde para los orgánicos aprovechables."
    ),
    note=(
        "Este resumen es una guía de estudio. Para el texto completo y su vigencia consulta la "
        "norma oficial del Ministerio de Ambiente y Desarrollo Sostenible."
    ),
)

PRACTICES: tuple[Practice, ...] = (
    Practice(
        "Separa desde el origen",
        "Clasifica el residuo en el momento en que lo desechas: mezclarlo después lo contamina.",
    ),
    Practice(
        "Limpio y seco",
        "Enjuaga los envases y retira los restos de comida: uno sucio puede arruinar el material.",
    ),
    Practice(
        "Reduce el volumen",
        "Aplasta botellas, latas y cajas: ocupan menos espacio en la bolsa y en el transporte.",
    ),
    Practice(
        "Evita lo desechable",
        "Lleva tu propio termo, vaso y bolsa: el mejor residuo es el que no se genera.",
    ),
    Practice(
        "Aprovecha lo orgánico",
        "Los restos de comida y de poda pueden ser compost si no se mezclan con plásticos.",
    ),
    Practice(
        "Pregunta antes de tirar",
        "Si dudas dónde va un residuo, escanéalo en EcoUMB o consulta esta guía antes de decidir.",
    ),
)
