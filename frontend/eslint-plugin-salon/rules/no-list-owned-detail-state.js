"use strict";

// Match files like src/app/dashboard/<entity>/page.tsx
const LIST_PAGE_RE = /src\/app\/dashboard\/[^/]+\/page\.tsx$/;
// Match imports like *DetailsDialog / *DetailDialog / *DetailDrawer / *DetailSheet
const DETAIL_IMPORT_RE = /Detail(s)?(Dialog|Drawer|Sheet)$/;

module.exports = {
  meta: {
    type: "problem",
    messages: {
      listOwnsDetail:
        "This list page owns entity detail state locally. Move detail to its canonical route under `app/dashboard/<entity>/[id]/page.tsx` and use an intercepting route at `@modal/(.)<entity>/[id]/page.tsx`. See design_system.md §7.5.",
    },
    schema: [],
  },
  create(context) {
    const filename = context.filename ?? context.getFilename();
    if (!LIST_PAGE_RE.test(filename.replace(/\\/g, "/"))) return {};

    let importsDetailDialog = false;
    let detailIdentifier = null;

    return {
      ImportDeclaration(node) {
        for (const spec of node.specifiers) {
          if (spec.type === "ImportSpecifier" && DETAIL_IMPORT_RE.test(spec.imported.name)) {
            importsDetailDialog = true;
            detailIdentifier = spec.imported.name;
          }
        }
      },
      "Program:exit"(node) {
        if (!importsDetailDialog) return;
        // Walk the file for a `useState` whose variable name suggests an entity ID
        const source = context.sourceCode ?? context.getSourceCode();
        const ID_NAME_RE = /^(selected|active|current)[A-Z].*Id$/;
        for (const tok of source.ast.body) {
          if (tok.type === "VariableDeclaration") walkForId(tok, context, ID_NAME_RE);
          if (tok.type === "ExportNamedDeclaration" && tok.declaration) walkForId(tok.declaration, context, ID_NAME_RE);
          if (tok.type === "ExportDefaultDeclaration" && tok.declaration) walkForId(tok.declaration, context, ID_NAME_RE);
          if (tok.type === "FunctionDeclaration") walkForId(tok, context, ID_NAME_RE);
        }
      },
    };

    function walkForId(node, context, idRe) {
      // Depth-limited recursive descent looking for `const [<idRe>, ...] = useState(...)`
      const stack = [node];
      while (stack.length) {
        const n = stack.pop();
        if (!n || typeof n !== "object") continue;
        if (
          n.type === "VariableDeclarator" &&
          n.id && n.id.type === "ArrayPattern" &&
          n.id.elements[0] &&
          n.id.elements[0].type === "Identifier" &&
          idRe.test(n.id.elements[0].name) &&
          n.init &&
          ((n.init.type === "CallExpression" && n.init.callee.name === "useState") ||
            (n.init.type === "CallExpression" && n.init.callee.type === "MemberExpression" && n.init.callee.property.name === "useState"))
        ) {
          context.report({ node: n, messageId: "listOwnsDetail" });
          return;
        }
        for (const k of Object.keys(n)) {
          if (k === "parent" || k === "tokens" || k === "comments" || k === "loc" || k === "range") continue;
          const v = n[k];
          if (Array.isArray(v)) {
            for (const item of v) {
              if (item && typeof item === "object" && item.type) stack.push(item);
            }
          } else if (v && typeof v === "object" && v.type) {
            stack.push(v);
          }
        }
      }
    }
  },
};
