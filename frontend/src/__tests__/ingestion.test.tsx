import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { DocumentSubmitForm } from "../components/ingestion/DocumentSubmitForm";
import { api } from "../services/api";

describe("Document Ingestion Form", () => {
  it("allows selecting scenario presets and submitting report", async () => {
    const mockSubmitRes = {
      status: "accepted" as const,
      message: "Document successfully ingested and pipeline processed",
      document_id: "doc-test-123",
      fused_events_affected: 2,
      signals_generated: 1,
      alerts_generated: 1,
      duplicate_of_id: null,
      error_detail: null,
      processing_time_ms: 45.2,
    };

    vi.spyOn(api, "submitDocument").mockResolvedValue(mockSubmitRes);
    const onSubmitted = vi.fn();

    render(<DocumentSubmitForm onDocumentSubmitted={onSubmitted} />);

    // Click on Nipah preset
    const presetBtn = screen.getByText("Nipah Alert (Kerala)");
    fireEvent.click(presetBtn);

    // Ensure title input populated
    const titleInput = screen.getByPlaceholderText("e.g. Nipah virus alert in Kozhikode...") as HTMLInputElement;
    expect(titleInput.value).toContain("Nipah");

    // Click submit button
    const submitBtn = screen.getByText("Submit to Continuous Pipeline");
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(screen.getByText(/Pipeline Status: ACCEPTED/i)).toBeInTheDocument();
      expect(screen.getByText(/Document successfully ingested/i)).toBeInTheDocument();
    });

    expect(onSubmitted).toHaveBeenCalledWith(mockSubmitRes);
  });
});
