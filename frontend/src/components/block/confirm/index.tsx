import React, { useState } from 'react';
import { create } from 'zustand';
import { devtools } from 'zustand/middleware';
import type { FieldValues, UseFormReturn } from 'react-hook-form';
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { cn } from '@/libs/utils';
import { Button } from '@/components/ui/button';

interface ConfirmDialogStore {
  open: boolean;
  content: React.ReactNode;
  className?: string;
  buttonText?: { cancel?: string; confirm?: string; loading?: string };
  operations?: (props: { setOpen: (value: boolean) => void }) => React.ReactNode[];
  onConfirm?: () => void | Promise<void>;
  setOpen: (value: boolean) => void;
  setContent: (content: React.ReactNode) => void;
  setOnConfirm: (onConfirm?: () => void) => void;
  setButtonText: (buttonText?: { cancel?: string; confirm?: string; loading?: string }) => void;
  setOperations: (operations?: (props: { setOpen: (value: boolean) => void }) => React.ReactNode[]) => void;
  setClassName: (className?: string) => void;
}

const useConfirmDialogStore = create<ConfirmDialogStore>()(
  devtools(set => ({
    open: false,
    content: null,
    className: undefined,
    buttonText: { cancel: 'Cancel', confirm: 'Confirm', loading: 'Processing' },
    operations: () => [],
    onConfirm: undefined,
    setOpen: (value: boolean) => set({ open: value }),
    setContent: content => set({ content }),
    setOnConfirm: onConfirm => set({ onConfirm }),
    setButtonText: buttonText => set({ buttonText }),
    setOperations: operations => set({ operations }),
    setClassName: className => set({ className }),
  })),
);

const ConfirmDialog = () => {
  const { open, content, buttonText, operations, onConfirm, setOpen, className } = useConfirmDialogStore();
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleConfirm = async () => {
    setIsSubmitting(true);
    try {
      await onConfirm?.();
    } finally {
      setIsSubmitting(false);
      setOpen(false);
    }
  };
  return (
    <Dialog open={open} onOpenChange={value => !isSubmitting && setOpen(value)}>
      <DialogHeader>
        <DialogTitle></DialogTitle>
      </DialogHeader>
      <DialogContent className={cn('w-[380px] pt-8 pr-4 pb-5 pl-6', className)}>
        <div>{content}</div>
        <DialogFooter>
          {operations ? (
            operations({ setOpen })
          ) : (
            <>
              <Button variant="secondary" onClick={() => setOpen(false)} disabled={isSubmitting}>
                {buttonText?.cancel || 'Cancel'}
              </Button>
              {buttonText?.confirm && (
                <Button onClick={handleConfirm} disabled={isSubmitting}>
                  {isSubmitting ? buttonText?.loading || 'Processing' : buttonText?.confirm || 'Confirm'}
                </Button>
              )}
            </>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};

ConfirmDialog.displayName = 'ConfirmDialog';

function confirm<F extends FieldValues = FieldValues, R = any>(props: {
  content: React.ReactNode | ((props: { form?: UseFormReturn<F> }) => React.ReactNode);
  className?: string;
  buttonText?: { cancel?: string; confirm?: string; loading?: string };
  operations?: (props: { setOpen: (value: boolean) => void }) => React.ReactNode[];
  onConfirm?: (formData?: F) => R | Promise<R>;
  form?: UseFormReturn<F>;
}) {
  const { setOpen, setContent, setOnConfirm, setButtonText, setOperations, setClassName } = useConfirmDialogStore.getState();

  const wrappedOnConfirm = async () => {
    if (props.form) {
      const formData = props.form.getValues();
      await props.onConfirm?.(formData);
    } else {
      await props.onConfirm?.();
    }
  };

  setContent(typeof props.content === 'function' ? props.content({ form: props.form }) : props.content);
  setOnConfirm(wrappedOnConfirm);
  setOperations(props.operations);
  setButtonText(props.buttonText);
  setClassName(props.className);
  setOpen(true);
}

export async function asyncConfirm<F extends FieldValues = FieldValues, R = any>(props: {
  content: React.ReactNode | ((props: { form?: UseFormReturn<F> }) => React.ReactNode);
  buttonText?: { cancel?: string; confirm?: string };
  operations?: (props: { setOpen: (value: boolean) => void }) => React.ReactNode[];
  onConfirm?: (formData?: F) => R | Promise<R>;
  form?: UseFormReturn<F>;
}) {
  const promise = new Promise<R>(resolve => {
    confirm<F>({
      content: props.content,
      buttonText: props.buttonText,
      operations: props.operations,
      form: props.form,
      onConfirm: async (formData?: F) => {
        if (!props.onConfirm) {
          resolve(undefined as any);
          return;
        }
        const res = await props.onConfirm(formData as any);
        resolve(res);
      },
    });
  });
  return promise;
}

export { ConfirmDialog, confirm };
