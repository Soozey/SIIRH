
/**
 * Helper to handle printing with dynamic title swapping.
 * Sets the document title to the filename before printing
 * and restores it afterwards.
 */
export const usePrint = (filename: string) => {
    const handlePrint = () => {
        const originalTitle = document.title;
        document.title = filename;
        window.print();
        document.title = originalTitle;
    };
    return handlePrint;
};
