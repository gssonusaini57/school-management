import { useState } from "react";
import { useTranslation } from "react-i18next";
import { FileDown } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Button } from "@/components/ui/button";
import { DatePicker } from "@/components/ui/date-picker";
import { toast } from "@/components/ui/toaster";
import { downloadPdf } from "@/lib/pdf";

type Format = "A" | "B";

export default function Letterheads() {
  const { t } = useTranslation();
  const today = new Date().toISOString().slice(0, 10);

  const [format, setFormat] = useState<Format>("A");
  const [ref, setRef] = useState("KIS/____");
  const [date, setDate] = useState(today);
  const [recipientName, setRecipientName] = useState("");
  const [recipientLines, setRecipientLines] = useState("");
  const [subjectEn, setSubjectEn] = useState("");
  const [subjectPa, setSubjectPa] = useState("");
  const [salutation, setSalutation] = useState("Respected Sir,");
  const [body, setBody] = useState("");
  const [closing, setClosing] = useState("Sincerely,");
  const [signName, setSignName] = useState("Gurpreet Singh");
  const [signRole, setSignRole] = useState("Principal");
  const [busy, setBusy] = useState(false);

  const generate = async () => {
    if (!subjectEn.trim()) return toast("Subject is required", "warning");
    if (!body.trim()) return toast("Body cannot be empty", "warning");
    if (!recipientName.trim()) return toast("Recipient name is required", "warning");

    const payload = {
      format,
      ref,
      date,
      recipient: {
        name: recipientName,
        lines: recipientLines.split("\n").map((s) => s.trim()).filter(Boolean),
      },
      subject: { en: subjectEn, pa: subjectPa || subjectEn },
      salutation,
      body: body.split(/\n\s*\n/).map((p) => p.trim()).filter(Boolean),
      closing,
      signatory: { name: signName, role: signRole },
    };

    setBusy(true);
    try {
      const kind = format === "A" ? "letterhead-a" : "letterhead-b";
      const stamp = ref.replace(/\W+/g, "-").replace(/^-|-$/g, "") || "letterhead";
      await downloadPdf(kind, payload, `${kind}-${stamp}.pdf`);
      toast(`Letterhead generated`, "success");
    } catch {
      /* downloadPdf already toasted */
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="space-y-4">
      <h1 className="font-display text-heading-lg text-deep-indigo">{t("portal.nav.letterheads", "Letterheads")}</h1>
      <p className="text-sm text-muted-foreground -mt-2">
        Generate brand-styled school letterheads on demand. Format A — classic centered seal for formal correspondence.
        Format B — modern asymmetric for day-to-day letters.
      </p>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <Card>
          <CardHeader><CardTitle>Letter details</CardTitle></CardHeader>
          <CardContent className="space-y-3">
            <div className="space-y-1.5">
              <Label>Format</Label>
              <div role="radiogroup" className="grid grid-cols-2 gap-2 p-1 rounded-md bg-secondary">
                {(["A", "B"] as const).map((f) => (
                  <button
                    key={f}
                    type="button"
                    role="radio"
                    aria-checked={format === f}
                    onClick={() => setFormat(f)}
                    className={`px-3 py-2 rounded text-sm font-semibold transition-colors ${
                      format === f ? "bg-primary text-primary-foreground" : "text-foreground hover:bg-background"
                    }`}
                  >
                    {f === "A" ? "A · Classic" : "B · Modern"}
                  </button>
                ))}
              </div>
            </div>

            <div className="grid grid-cols-2 gap-2">
              <div className="space-y-1.5">
                <Label>Reference no.</Label>
                <Input value={ref} onChange={(e) => setRef(e.target.value)} />
              </div>
              <div className="space-y-1.5">
                <Label>Date</Label>
                <DatePicker value={date} onChange={setDate} />
              </div>
            </div>

            <div className="space-y-1.5">
              <Label>Recipient name</Label>
              <Input value={recipientName} onChange={(e) => setRecipientName(e.target.value)} placeholder="Sh. Gurpreet Singh" />
            </div>
            <div className="space-y-1.5">
              <Label>Recipient address (one line each)</Label>
              <Textarea value={recipientLines} onChange={(e) => setRecipientLines(e.target.value)} rows={3} placeholder={"#142, Mohalla Sangat Sar\nJalalabad, District Patiala\nPunjab — 147001"} />
            </div>

            <div className="grid grid-cols-2 gap-2">
              <div className="space-y-1.5">
                <Label>Subject (English) *</Label>
                <Input value={subjectEn} onChange={(e) => setSubjectEn(e.target.value)} required />
              </div>
              <div className="space-y-1.5">
                <Label>Subject (ਪੰਜਾਬੀ)</Label>
                <Input value={subjectPa} onChange={(e) => setSubjectPa(e.target.value)} className="font-gurmukhi" />
              </div>
            </div>

            <div className="space-y-1.5">
              <Label>Salutation</Label>
              <Input value={salutation} onChange={(e) => setSalutation(e.target.value)} />
            </div>
            <div className="space-y-1.5">
              <Label>Body (separate paragraphs with a blank line) *</Label>
              <Textarea value={body} onChange={(e) => setBody(e.target.value)} rows={9} placeholder="First paragraph…&#10;&#10;Second paragraph…" />
            </div>
            <div className="space-y-1.5">
              <Label>Closing</Label>
              <Input value={closing} onChange={(e) => setClosing(e.target.value)} />
            </div>

            <div className="grid grid-cols-2 gap-2">
              <div className="space-y-1.5">
                <Label>Signatory name</Label>
                <Input value={signName} onChange={(e) => setSignName(e.target.value)} />
              </div>
              <div className="space-y-1.5">
                <Label>Signatory role</Label>
                <Input value={signRole} onChange={(e) => setSignRole(e.target.value)} />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader><CardTitle>About the formats</CardTitle></CardHeader>
          <CardContent className="space-y-4 text-sm">
            <div>
              <div className="font-semibold text-deep-indigo">Format A · Classic</div>
              <p className="text-muted-foreground">
                Centered crest, school name in Playfair Display, full Punjabi line, contact strip and a tri-color band.
                Use for appointment orders, formal notices to the Board, official correspondence.
              </p>
            </div>
            <div>
              <div className="font-semibold text-deep-indigo">Format B · Modern</div>
              <p className="text-muted-foreground">
                Asymmetric crest + name layout with a gold/red accent strip. Use for day-to-day letters such as PTM
                invitations, parent circulars, or routine outbound mail.
              </p>
            </div>
            <div className="rounded-md bg-cream/40 border border-border p-3 text-xs text-muted-foreground">
              <p className="font-semibold text-foreground mb-1">Tips</p>
              <ul className="list-disc pl-4 space-y-0.5">
                <li>Punjabi subject line falls back to the English text if you leave it blank.</li>
                <li>Each blank line in the body starts a new paragraph.</li>
                <li>The PDF is generated server-side and downloads as <code>letterhead-{format.toLowerCase()}-&lt;ref&gt;.pdf</code>.</li>
              </ul>
            </div>
            <Button className="w-full" onClick={generate} disabled={busy}>
              <FileDown className="h-4 w-4" /> {busy ? "Generating…" : `Generate Format ${format} PDF`}
            </Button>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
