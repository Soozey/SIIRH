import { useState } from "react";

export interface CascadingSelectValue {
  etablissement?: number;
  departement?: number;
  service?: number;
  unite?: number;
}

export const useOrganizationalSelection = (
  initialValue: CascadingSelectValue = {},
) => {
  const [value, setValue] = useState<CascadingSelectValue>(initialValue);

  const reset = () => setValue({});

  const setEtablissement = (etablissementId: number | undefined) => {
    setValue({
      etablissement: etablissementId,
      departement: undefined,
      service: undefined,
      unite: undefined,
    });
  };

  const setDepartement = (departementId: number | undefined) => {
    setValue((prev) => ({
      ...prev,
      departement: departementId,
      service: undefined,
      unite: undefined,
    }));
  };

  const setService = (serviceId: number | undefined) => {
    setValue((prev) => ({
      ...prev,
      service: serviceId,
      unite: undefined,
    }));
  };

  const setUnite = (uniteId: number | undefined) => {
    setValue((prev) => ({
      ...prev,
      unite: uniteId,
    }));
  };

  const isComplete = (requiredLevels: (keyof CascadingSelectValue)[] = []) => {
    return requiredLevels.every((level) => value[level] !== undefined);
  };

  const getPath = () => {
    const parts: string[] = [];
    if (value.etablissement) parts.push("etablissement");
    if (value.departement) parts.push("departement");
    if (value.service) parts.push("service");
    if (value.unite) parts.push("unite");
    return parts;
  };

  return {
    value,
    setValue,
    reset,
    setEtablissement,
    setDepartement,
    setService,
    setUnite,
    isComplete,
    getPath,
  };
};
