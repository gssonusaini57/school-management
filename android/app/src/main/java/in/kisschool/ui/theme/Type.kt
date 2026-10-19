package `in`.kisschool.ui.theme

import androidx.compose.ui.text.font.Font
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import `in`.kisschool.R

/**
 * Playfair Display Bold, the brand's display face (--font-display on the website). Bundled
 * as res/font/playfair_display_bold.ttf under the SIL Open Font License, whose text ships in
 * assets/fonts/PlayfairDisplay-OFL.txt.
 *
 * Kept for the few brand moments only: the Home greeting, the school name in headers and
 * the drawer header. Everything else stays in the default sans.
 */
val PlayfairDisplay: FontFamily = FontFamily(Font(R.font.playfair_display_bold, FontWeight.Bold))
