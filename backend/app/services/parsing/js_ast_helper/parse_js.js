#!/usr/bin/env node
/**
 * Reads JS/TS/JSX/TSX source from stdin, parses it with @babel/parser,
 * walks it with @babel/traverse, and prints a JSON object to stdout:
 *
 *   {
 *     "entities": [
 *       {"entity_type": "function"|"class"|"method", "name": str,
 *        "start_line": int, "end_line": int, "signature": str,
 *        "calls": [str, ...], "bases": [str, ...]}
 *     ],
 *     "imports": [
 *       {"source": str, "names": [str, ...]}
 *     ]
 *   }
 *
 * This is a best-effort static structural extraction. It never evaluates
 * or executes the source it's given -- parsing to an AST only.
 */

const parser = require("@babel/parser");
const traverse = require("@babel/traverse").default;

function readStdin() {
  return new Promise((resolve, reject) => {
    let data = "";
    process.stdin.setEncoding("utf8");
    process.stdin.on("data", (chunk) => (data += chunk));
    process.stdin.on("end", () => resolve(data));
    process.stdin.on("error", reject);
  });
}

function paramsToSignature(name, params) {
  const parts = params.map((p) => {
    if (p.type === "Identifier") return p.name;
    if (p.type === "AssignmentPattern" && p.left.type === "Identifier")
      return p.left.name + "=...";
    if (p.type === "RestElement" && p.left && p.left.name)
      return "..." + p.left.name;
    if (p.type === "ObjectPattern") return "{...}";
    if (p.type === "ArrayPattern") return "[...]";
    return "arg";
  });
  return `${name}(${parts.join(", ")})`;
}

function collectCalls(path) {
  const calls = new Set();
  path.traverse({
    CallExpression(inner) {
      const callee = inner.node.callee;
      if (callee.type === "Identifier") {
        calls.add(callee.name);
      } else if (callee.type === "MemberExpression" && callee.property.type === "Identifier") {
        calls.add(callee.property.name);
      }
    },
  });
  return Array.from(calls);
}

async function main() {
  const source = await readStdin();
  const entities = [];
  const imports = [];

  let ast;
  try {
    ast = parser.parse(source, {
      sourceType: "module",
      plugins: ["jsx", "typescript", "classProperties", "optionalChaining", "nullishCoalescingOperator"],
      errorRecovery: true,
    });
  } catch (err) {
    // Parsing failed entirely -- report empty result, let the caller fall back.
    process.stdout.write(JSON.stringify({ entities: [], imports: [], error: String(err.message || err) }));
    return;
  }

  traverse(ast, {
    ImportDeclaration(path) {
      const source = path.node.source.value;
      const names = path.node.specifiers.map((s) => {
        if (s.type === "ImportDefaultSpecifier") return s.local.name;
        if (s.type === "ImportNamespaceSpecifier") return "*as " + s.local.name;
        return s.imported ? s.imported.name : s.local.name;
      });
      imports.push({ source, names });
    },
    FunctionDeclaration(path) {
      const node = path.node;
      if (!node.id) return; // anonymous, skip
      entities.push({
        entity_type: "function",
        name: node.id.name,
        start_line: node.loc ? node.loc.start.line : null,
        end_line: node.loc ? node.loc.end.line : null,
        signature: paramsToSignature(node.id.name, node.params),
        calls: collectCalls(path),
        bases: [],
      });
    },
    VariableDeclarator(path) {
      const node = path.node;
      const init = node.init;
      if (
        node.id.type === "Identifier" &&
        init &&
        (init.type === "ArrowFunctionExpression" || init.type === "FunctionExpression")
      ) {
        entities.push({
          entity_type: "function",
          name: node.id.name,
          start_line: node.loc ? node.loc.start.line : null,
          end_line: init.loc ? init.loc.end.line : null,
          signature: paramsToSignature(node.id.name, init.params),
          calls: collectCalls(path.get("init")),
          bases: [],
        });
      }
    },
    ClassDeclaration(path) {
      const node = path.node;
      if (!node.id) return;
      const bases = [];
      if (node.superClass && node.superClass.type === "Identifier") {
        bases.push(node.superClass.name);
      }
      entities.push({
        entity_type: "class",
        name: node.id.name,
        start_line: node.loc ? node.loc.start.line : null,
        end_line: node.loc ? node.loc.end.line : null,
        signature: `class ${node.id.name}${bases.length ? " extends " + bases[0] : ""}`,
        calls: [],
        bases,
      });
      node.body.body.forEach((member) => {
        if (member.type === "ClassMethod" || member.type === "ClassPrivateMethod") {
          const methodName =
            member.key.type === "Identifier" ? member.key.name : String(member.key.value || "anonymous");
          const methodPath = path
            .get("body")
            .get("body")
            .find((p) => p.node === member);
          entities.push({
            entity_type: "method",
            name: `${node.id.name}.${methodName}`,
            start_line: member.loc ? member.loc.start.line : null,
            end_line: member.loc ? member.loc.end.line : null,
            signature: paramsToSignature(methodName, member.params),
            calls: methodPath ? collectCalls(methodPath) : [],
            bases: [],
          });
        }
      });
    },
  });

  process.stdout.write(JSON.stringify({ entities, imports }));
}

main().catch((err) => {
  process.stdout.write(JSON.stringify({ entities: [], imports: [], error: String(err.message || err) }));
});
