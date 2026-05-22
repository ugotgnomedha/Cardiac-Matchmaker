import {
  Description,
  Input,
  Label,
  ListBox,
  Select,
  TextArea,
  TextField,
} from "@heroui/react";
import type { Key } from "react";

export type FormFieldOption = {
  label: string;
  value: string;
};

export type FormFieldConfig = {
  autoComplete?: string;
  description: string;
  inputMode?: "text" | "search" | "email" | "tel" | "url" | "numeric";
  kind: "input" | "textarea" | "select";
  label: string;
  maxLength?: number;
  name: string;
  onChange: (value: string) => void;
  options?: FormFieldOption[];
  placeholder: string;
  required?: boolean;
  rows?: number;
  type?: "email" | "password" | "text";
  value: string;
};

export function FormFields({ fields }: { fields: FormFieldConfig[] }) {
  return (
    <>
      {fields.map((field) => (
        <FormField key={field.name} field={field} />
      ))}
    </>
  );
}

function FormField({ field }: { field: FormFieldConfig }) {
  if (field.kind === "select") {
    return <SelectField field={field} />;
  }

  return (
    <TextField
      className="grid gap-2"
      fullWidth
      isRequired={field.required}
      name={field.name}
      type={field.type}
      value={field.value}
      onChange={field.onChange}
    >
      <Label className="text-sm font-medium text-zinc-700">
        {field.label}
      </Label>
      {field.kind === "textarea" ? (
        <TextArea
          className="min-h-28 rounded-lg border border-zinc-300 px-3 py-2 text-zinc-950 outline-none focus:border-teal-600"
          fullWidth
          inputMode={field.inputMode}
          maxLength={field.maxLength}
          placeholder={field.placeholder}
          rows={field.rows}
        />
      ) : (
        <Input
          autoComplete={field.autoComplete}
          className="h-10 rounded-lg border border-zinc-300 px-3 text-zinc-950 outline-none focus:border-teal-600"
          fullWidth
          inputMode={field.inputMode}
          maxLength={field.maxLength}
          placeholder={field.placeholder}
        />
      )}
      <Description className="text-xs leading-5 text-zinc-500">
        {field.description}
      </Description>
    </TextField>
  );
}

function SelectField({ field }: { field: FormFieldConfig }) {
  function handleSelectionChange(key: Key | null) {
    if (key === null) {
      return;
    }

    field.onChange(String(key));
  }

  return (
    <Select
      className="grid gap-2"
      fullWidth
      isRequired={field.required}
      name={field.name}
      onSelectionChange={handleSelectionChange}
      placeholder={field.placeholder}
      selectedKey={field.value}
    >
      <Label className="text-sm font-medium text-zinc-700">
        {field.label}
      </Label>
      <Select.Trigger className="flex h-10 w-full items-center justify-between rounded-lg border border-zinc-300 px-3 text-left text-zinc-950 outline-none focus:border-teal-600">
        <Select.Value />
        <Select.Indicator />
      </Select.Trigger>
      <Description className="text-xs leading-5 text-zinc-500">
        {field.description}
      </Description>
      <Select.Popover>
        <ListBox>
          {(field.options ?? []).map((option) => (
            <ListBox.Item
              id={option.value}
              key={option.value}
              textValue={option.label}
            >
              {option.label}
            </ListBox.Item>
          ))}
        </ListBox>
      </Select.Popover>
    </Select>
  );
}
