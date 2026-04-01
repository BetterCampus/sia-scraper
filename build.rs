use scraper::Selector;
use std::fs;
use std::path::Path;
use syn::{
    Expr, ExprCall, ExprClosure, ExprLit, ExprMethodCall, File, Item, ItemStatic, Lit, Stmt,
};

fn main() {
    let parser_path = Path::new("rust/src/parsers/course_parser.rs");

    let content = fs::read_to_string(parser_path)
        .unwrap_or_else(|e| panic!("Failed to read {}: {}", parser_path.display(), e));

    let syntax_tree: File = syn::parse_file(&content).unwrap_or_else(|e| {
        panic!(
            "Failed to parse Rust syntax in {}: {}",
            parser_path.display(),
            e
        )
    });

    let mut selector_count = 0;

    for item in syntax_tree.items {
        if let Item::Static(item_static) = item {
            if is_selector_static(&item_static) {
                let selector_name = item_static.ident.to_string();

                if let Some(selector_str) = extract_selector_string(&item_static) {
                    if let Err(e) = Selector::parse(&selector_str) {
                        panic!(
                            "Invalid CSS selector in {}: '{}'\nError: {:?}",
                            selector_name, selector_str, e
                        );
                    }

                    println!(
                        "cargo:warning=Validated selector {}: '{}'",
                        selector_name, selector_str
                    );
                    selector_count += 1;
                } else {
                    panic!("Failed to extract selector string from {}", selector_name);
                }
            }
        }
    }

    if selector_count == 0 {
        panic!(
            "No selectors found in {}! Expected LazyLock<Selector> statics.",
            parser_path.display()
        );
    }

    println!(
        "cargo:warning=Successfully validated {} CSS selectors",
        selector_count
    );
    println!("cargo:rerun-if-changed={}", parser_path.display());
    println!("cargo:rerun-if-changed=build.rs");
}

fn is_selector_static(item: &ItemStatic) -> bool {
    let type_str = quote::quote!(#item.ty).to_string();
    type_str.contains("LazyLock") && type_str.contains("Selector")
}

fn extract_selector_string(item: &ItemStatic) -> Option<String> {
    if let Expr::Call(ExprCall { args, .. }) = &*item.expr {
        if let Some(Expr::Closure(ExprClosure { body, .. })) = args.first() {
            return extract_from_expr(body);
        }
    }
    None
}

fn extract_from_expr(expr: &Expr) -> Option<String> {
    match expr {
        Expr::MethodCall(method_call) => extract_from_method_call(method_call),
        Expr::Block(block_expr) => {
            if let Some(Stmt::Expr(inner_expr, _)) = block_expr.block.stmts.last() {
                extract_from_expr(inner_expr)
            } else {
                None
            }
        }
        _ => None,
    }
}

fn extract_from_method_call(method_call: &ExprMethodCall) -> Option<String> {
    if method_call.method == "unwrap" {
        if let Expr::Call(inner_call) = &*method_call.receiver {
            if let Some(Expr::Lit(ExprLit {
                lit: Lit::Str(lit_str),
                ..
            })) = inner_call.args.first()
            {
                return Some(lit_str.value());
            }
        }
    }
    None
}
