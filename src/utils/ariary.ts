import { formatNumber } from "./format";

export const formatAriary = (amount: number | null | undefined): string => {
  return `${formatNumber(amount, 2)} Ariary`;
};
