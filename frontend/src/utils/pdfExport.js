/**
 * PDF Export Utility for MachineSense
 *
 * Captures rendered DOM elements and generates a high-resolution, multi-page PDF document
 * using html2canvas and jsPDF.
 * 
 */

import jsPDF from 'jspdf';
import html2canvas from 'html2canvas';

/**
 * Capture an array of page elements and assemble them into a multi-page A4 PDF.
 *
 * @param {HTMLElement[]} pageElements - Array of page container DOM elements
 * @param {string} filename - Target output PDF filename (e.g. MachineSense_Report_MCH-001.pdf)
 * @param {Object} [options] - Additional render options
 * @returns {Promise<void>}
 */
export async function exportPagesToPDF(pageElements, filename = 'MachineSense_Report.pdf', options = {}) {
  if (!pageElements || pageElements.length === 0) {
    throw new Error('No page elements provided for PDF export');
  }

  // Create A4 PDF instance (210mm x 297mm)
  const pdf = new jsPDF({
    orientation: 'portrait',
    unit: 'mm',
    format: 'a4',
    compress: true,
  });

  const pdfWidth = pdf.internal.pageSize.getWidth(); // 210mm
  const pdfHeight = pdf.internal.pageSize.getHeight(); // 297mm

  for (let i = 0; i < pageElements.length; i++) {
    const el = pageElements[i];
    if (!el) continue;

    // Render page element to high-DPI canvas
    const canvas = await html2canvas(el, {
      scale: options.scale || 2, // 2x scaling for crisp retina text and charts
      useCORS: true,
      logging: false,
      backgroundColor: options.backgroundColor || '#0a0d14',
      windowWidth: options.windowWidth || 950,
    });

    const imgData = canvas.toDataURL('image/jpeg', 0.95);

    if (i > 0) {
      pdf.addPage();
    }

    // Scale canvas to fit exactly into A4 dimensions
    const imgWidth = pdfWidth;
    const imgHeight = (canvas.height * pdfWidth) / canvas.width;

    // Center vertically if content is shorter than full A4 page, otherwise draw at top
    const yOffset = imgHeight < pdfHeight ? (pdfHeight - imgHeight) / 2 : 0;
    pdf.addImage(imgData, 'JPEG', 0, Math.max(0, yOffset), imgWidth, Math.min(imgHeight, pdfHeight));
  }

  pdf.save(filename);
}

/**
 * Export a container element to PDF. If the container contains elements with
 * [data-pdf-page], captures each as an independent page to ensure charts and
 * cards are never sliced across page boundaries.
 *
 * @param {HTMLElement} containerElement - Root DOM element to capture
 * @param {string} filename - Output filename
 * @param {Object} [options] - Rendering options
 * @returns {Promise<void>}
 */
export async function exportElementToPDF(containerElement, filename = 'MachineSense_Report.pdf', options = {}) {
  if (!containerElement) {
    throw new Error('Target element not found for PDF export');
  }

  // Check if multiple structured pages are defined
  const pageNodes = containerElement.querySelectorAll('[data-pdf-page]');
  if (pageNodes && pageNodes.length > 0) {
    return exportPagesToPDF(Array.from(pageNodes), filename, options);
  }

  // Fallback: render single element to canvas and slice cleanly into A4 pages
  const canvas = await html2canvas(containerElement, {
    scale: options.scale || 2,
    useCORS: true,
    logging: false,
    backgroundColor: options.backgroundColor || '#0a0d14',
  });

  const pdf = new jsPDF({
    orientation: 'portrait',
    unit: 'mm',
    format: 'a4',
    compress: true,
  });

  const pdfWidth = pdf.internal.pageSize.getWidth();
  const pdfHeight = pdf.internal.pageSize.getHeight();
  const pageCanvasHeight = (canvas.width * pdfHeight) / pdfWidth;

  let renderedHeight = 0;
  let pageIndex = 0;

  while (renderedHeight < canvas.height) {
    if (pageIndex > 0) {
      pdf.addPage();
    }

    const currentSliceHeight = Math.min(pageCanvasHeight, canvas.height - renderedHeight);

    const pageCanvas = document.createElement('canvas');
    pageCanvas.width = canvas.width;
    pageCanvas.height = pageCanvasHeight;
    const ctx = pageCanvas.getContext('2d');

    // Fill background
    ctx.fillStyle = options.backgroundColor || '#0a0d14';
    ctx.fillRect(0, 0, pageCanvas.width, pageCanvas.height);

    // Draw the current page slice
    ctx.drawImage(
      canvas,
      0, renderedHeight, canvas.width, currentSliceHeight,
      0, 0, canvas.width, currentSliceHeight
    );

    const imgData = pageCanvas.toDataURL('image/jpeg', 0.95);
    pdf.addImage(imgData, 'JPEG', 0, 0, pdfWidth, pdfHeight);

    renderedHeight += currentSliceHeight;
    pageIndex++;
  }

  pdf.save(filename);
}

export default {
  exportPagesToPDF,
  exportElementToPDF,
};
