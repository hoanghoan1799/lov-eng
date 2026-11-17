import { z } from "zod";

const slugSchema = z.string().regex(/^[a-z0-9]+(-[a-z0-9]+)*$/, "use lowercase-kebab-case");

export const cefrSchema = z.enum(["A1", "A2", "B1", "B2"]);
export const phaseSchema = z.enum(["mvp", "beta", "v1"]);

export const localizedTextSchema = z.object({
  vi: z.string().min(1),
  en: z.string().min(1),
});

export const destinationSchema = z.object({
  id: slugSchema,
  order: z.number().int().min(1),
  name: localizedTextSchema,
  cefr: cefrSchema,
  scene: slugSchema,
  isHub: z.boolean().default(false),
  phase: phaseSchema,
  situations: z.array(z.string().min(1)).min(1),
  /** Ids of authored missions. Empty until the content is written. */
  missions: z.array(slugSchema),
});

export const pathFileSchema = z
  .object({
    version: z.literal(1),
    destinations: z.array(destinationSchema).min(1),
  })
  .superRefine((file, context) => {
    const ids = new Set<string>();

    file.destinations.forEach((destination, index) => {
      if (ids.has(destination.id)) {
        context.addIssue({ code: "custom", message: `duplicate destination id ${destination.id}` });
      }

      ids.add(destination.id);

      if (destination.order !== index + 1) {
        context.addIssue({
          code: "custom",
          message: `destination ${destination.id} has order ${destination.order}, expected ${index + 1}`,
        });
      }
    });

    if (file.destinations[0] && !file.destinations[0].isHub) {
      context.addIssue({ code: "custom", message: "the first destination must be the hub" });
    }
  });

export const turnSchema = z.object({
  id: slugSchema,
  /** Variants of the NPC line, so repeated plays do not feel identical. */
  npcLines: z.array(z.string().min(1)).min(1),
  /** Vietnamese translation of the first NPC line. */
  translation: z.string().min(1),
  /** Sentences the learner may say to pass this turn. */
  accepted: z.array(z.string().min(1)).min(1),
  hint: z.string().min(1),
});

export const missionSchema = z.object({
  id: slugSchema,
  destinationId: slugSchema,
  title: localizedTextSchema,
  cefr: cefrSchema,
  turns: z.array(turnSchema).min(1),
  rewardXp: z.number().int().positive(),
});

export type Cefr = z.infer<typeof cefrSchema>;
export type Destination = z.infer<typeof destinationSchema>;
export type PathFile = z.infer<typeof pathFileSchema>;
export type Turn = z.infer<typeof turnSchema>;
export type Mission = z.infer<typeof missionSchema>;
