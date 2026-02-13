import React from "react";
import { Document, Page, Text, View, StyleSheet, renderToFile } from "@react-pdf/renderer";

const styles = StyleSheet.create({
  page: { flexDirection: "column", backgroundColor: "#fff", padding: 40, paddingBottom: 60 },
  title: { fontSize: 24, marginBottom: 20, fontWeight: "bold" },
  text: { fontSize: 12, lineHeight: 1.5, marginBottom: 8 },
  section: { marginBottom: 20 },

  // wrap={false} on the parent View makes this block unbreakable —
  // if it doesn't fit, it moves entirely to the next page
  card: {
    border: "1px solid #ccc",
    borderRadius: 4,
    padding: 12,
    marginBottom: 10,
    backgroundColor: "#fafafa",
  },

  // fixed + absolute positioning = footer on every page
  footer: {
    position: "absolute",
    bottom: 25,
    left: 40,
    right: 40,
    textAlign: "center",
    fontSize: 9,
    color: "#999",
  },
});

const filler = "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris.";

const MyDocument = () => (
  <Document>
    <Page size="A4" style={styles.page}>
      <Text style={styles.title}>Advanced Features Demo</Text>

      {/* Generate enough content to trigger page breaks */}
      {Array.from({ length: 8 }, (_, i) => (
        // wrap={false} — keeps each card together on one page
        <View key={i} wrap={false} style={styles.card}>
          <Text style={[styles.text, { fontWeight: "bold" }]}>Card {i + 1}</Text>
          <Text style={styles.text}>{filler}</Text>
        </View>
      ))}

      {/* fixed — renders this Text on every page */}
      {/* render prop — gives access to pageNumber / totalPages */}
      <Text
        style={styles.footer}
        fixed
        render={({ pageNumber, totalPages }) => `Page ${pageNumber} of ${totalPages}`}
      />
    </Page>
  </Document>
);

(async () => {
  await renderToFile(<MyDocument />, "./output.pdf");
  console.log("PDF saved!");
})();
