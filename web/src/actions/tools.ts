'use server';
import { AuthWrapperContext, withUserAuth } from '@/lib/auth-wrapper';
import { decryptWithPrivateKey, encryptWithPublicKey } from '@/lib/crypto';
import { maskDataForFlatObject } from '@/lib/maskdata';
import { prisma } from '@/lib/prisma';
import Ajv from 'ajv';
import fs from 'fs';
import { JSONSchema } from 'json-schema-to-ts';
import path from 'path';

const MANUS_URL = process.env.MANUS_URL || 'http://localhost:5172';

const publicKey = fs.readFileSync(path.join(process.cwd(), 'keys', 'public.pem'), 'utf8');
const privateKey = fs.readFileSync(path.join(process.cwd(), 'keys', 'private.pem'), 'utf8');

const ajv = new Ajv();

export const getOrganizationToolsInfo = withUserAuth(async ({ organization }: AuthWrapperContext<{}>) => {
  // Get system tools
  const systemTools = await fetch(`${MANUS_URL}/tools`)
    .then(res => res.json() as Promise<{ name: string; type: 'tool' | 'mcp'; description: string; parameters: JSONSchema }[]>)
    .then(res => res.map(r => ({ ...r, id: r.name })));

  // Get organization custom tools
  const organizationTools = await prisma.organizationTools
    .findMany({
      where: {
        organizationId: organization.id,
      },
      include: {
        tool: true,
      },
    })
    .then(res =>
      res.map(r => ({
        id: r.tool.id,
        name: r.tool.name,
        type: 'mcp',
        description: r.tool.description,
      })),
    );

  return [...systemTools, ...organizationTools];
});

export const installTool = withUserAuth(async ({ organization, args }: AuthWrapperContext<{ toolId: string; env: Record<string, string> }>) => {
  const { toolId, env } = args;
  const tool = await prisma.tools.findUnique({
    where: { id: toolId },
  });

  if (!tool) {
    throw new Error('Tool not found');
  }

  const envSchema = tool.envSchema as JSONSchema;

  const validate = ajv.compile(envSchema);
  const isValid = validate(env);

  if (!isValid) {
    throw new Error(`Invalid environment variables config: ${JSON.stringify(validate.errors)}`);
  }

  const existing = await prisma.organizationTools.findUnique({
    where: { id: toolId, organizationId: organization.id },
  });

  if (existing) {
    await prisma.organizationTools.update({
      where: { id: toolId, organizationId: organization.id },
      data: { env: encryptWithPublicKey(JSON.stringify(env), publicKey) },
    });
  } else {
    await prisma.organizationTools.create({
      data: {
        organizationId: organization.id,
        toolId: toolId,
        env: encryptWithPublicKey(JSON.stringify(env), publicKey),
      },
    });
  }
});

export const closeTool = withUserAuth(async ({ organization, args }: AuthWrapperContext<{ toolId: string }>) => {
  const { toolId } = args;
  await prisma.organizationTools.delete({
    where: { id: toolId, organizationId: organization.id },
  });
});

/**
 * get all Tools from marketplace
 */
export const getToolsInfo = withUserAuth(async ({}: AuthWrapperContext<{}>) => {
  const tools = await prisma.tools.findMany({});
  return tools;
});
