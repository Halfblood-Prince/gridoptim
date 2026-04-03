// SPDX-License-Identifier: Zlib
/*
 * TINYEXPR - Tiny recursive descent parser and evaluation engine in C
 *
 * Copyright (c) 2015-2020 Lewis Van Winkle
 *
 * http://CodePlea.com
 *
 * This software is provided 'as-is', without any express or implied
 * warranty. In no event will the authors be held liable for any damages
 * arising from the use of this software.
 *
 * Permission is granted to anyone to use this software for any purpose,
 * including commercial applications, and to alter it and redistribute it
 * freely, subject to the following restrictions:
 *
 * 1. The origin of this software must not be misrepresented; you must not
 * claim that you wrote the original software. If you use this software
 * in a product, an acknowledgement in the product documentation would be
 * appreciated but is not required.
 * 2. Altered source versions must be plainly marked as such, and must not be
 * misrepresented as being the original software.
 * 3. This notice may not be removed or altered from any source distribution.
 */

/* COMPILE TIME OPTIONS */

/* Exponentiation associativity:
For a^b^c = (a^b)^c and -a^b = (-a)^b do nothing.
For a^b^c = a^(b^c) and -a^b = -(a^b) uncomment the next line.*/
/* #define TE_POW_FROM_RIGHT */

/* Logarithms
For log = base 10 log do nothing
For log = natural log uncomment the next line. */
/* #define TE_NAT_LOG */

#include "tinyexpr.h"
#include <stdlib.h>
#include <math.h>
#include <string.h>
#include <stdio.h>
#include <ctype.h>
#include <limits.h>

#ifndef NAN
#define NAN (0.0/0.0)
#endif

#ifndef INFINITY
#define INFINITY (1.0/0.0)
#endif


typedef double (*te_fun2)(double, double);

enum {
    TOK_NULL = TE_CLOSURE7+1, TOK_ERROR, TOK_END, TOK_SEP,
    TOK_OPEN, TOK_CLOSE, TOK_NUMBER, TOK_VARIABLE, TOK_INFIX
};


enum {TE_CONSTANT = 1};


typedef struct state {
    const char *start;
    const char *next;
    int type;
    union {double value; const double *bound; const void *function;};
    void *context;

    const te_variable *lookup;
    int lookup_len;
} state;


#define TYPE_MASK(TYPE) ((TYPE)&0x0000001F)

#define IS_PURE(TYPE) (((TYPE) & TE_FLAG_PURE) != 0)
#define IS_FUNCTION(TYPE) (((TYPE) & TE_FUNCTION0) != 0)
#define IS_CLOSURE(TYPE) (((TYPE) & TE_CLOSURE0) != 0)
#define ARITY(TYPE) ( ((TYPE) & (TE_FUNCTION0 | TE_CLOSURE0)) ? ((TYPE) & 0x00000007) : 0 )
#define NEW_EXPR(type, ...) new_expr((type), (const te_expr*[]){__VA_ARGS__})
#define CHECK_NULL(ptr, ...) if ((ptr) == NULL) { __VA_ARGS__; return NULL; }

static te_expr *new_expr(const int type, const te_expr *parameters[]) {
    const int arity = ARITY(type);
    const int psize = sizeof(void*) * arity;
    const int size = (sizeof(te_expr) - sizeof(void*)) + psize + (IS_CLOSURE(type) ? sizeof(void*) : 0);
    te_expr *ret = malloc(size);
    CHECK_NULL(ret);

    memset(ret, 0, size);
    if (arity && parameters) {
        memcpy(ret->parameters, parameters, psize);
    }
    ret->type = type;
    ret->bound = 0;
    return ret;
}


void te_free_parameters(te_expr *n) {
    if (!n) return;
    switch (TYPE_MASK(n->type)) {
        case TE_FUNCTION7: case TE_CLOSURE7: te_free(n->parameters[6]);     /* Falls through. */
        case TE_FUNCTION6: case TE_CLOSURE6: te_free(n->parameters[5]);     /* Falls through. */
        case TE_FUNCTION5: case TE_CLOSURE5: te_free(n->parameters[4]);     /* Falls through. */
        case TE_FUNCTION4: case TE_CLOSURE4: te_free(n->parameters[3]);     /* Falls through. */
        case TE_FUNCTION3: case TE_CLOSURE3: te_free(n->parameters[2]);     /* Falls through. */
        case TE_FUNCTION2: case TE_CLOSURE2: te_free(n->parameters[1]);     /* Falls through. */
        case TE_FUNCTION1: case TE_CLOSURE1: te_free(n->parameters[0]);
    }
}


void te_free(te_expr *n) {
    if (!n) return;
    te_free_parameters(n);
    free(n);
}


static double pi(void) {return 3.14159265358979323846;}
static double e(void) {return 2.71828182845904523536;}
static double fac(double a) {/* simplest version of fac */
    if (a < 0.0)
        return NAN;
    if (a > UINT_MAX)
        return INFINITY;
    unsigned int ua = (unsigned int)(a);
    unsigned long int result = 1, i;
    for (i = 1; i <= ua; i++) {
        if (i > ULONG_MAX / result)
            return INFINITY;
        result *= i;
    }
    return (double)result;
}
static double ncr(double n, double r) {
    if (n < 0.0 || r < 0.0 || n < r) return NAN;
    if (n > UINT_MAX || r > UINT_MAX) return INFINITY;
    unsigned long int un = (unsigned int)(n), ur = (unsigned int)(r), i;
    unsigned long int result = 1;
    if (ur > un / 2) ur = un - ur;
    for (i = 1; i <= ur; i++) {
        if (result > ULONG_MAX / (un - ur + i))
            return INFINITY;
        result *= un - ur + i;
        result /= i;
    }
    return result;
}
static double npr(double n, double r) {return ncr(n, r) * fac(r);}

#ifdef _MSC_VER
#pragma function (ceil)
#pragma function (floor)
#endif

static const te_variable functions[] = {
    /* must be in alphabetical order */
    {"abs", fabs,     TE_FUNCTION1 | TE_FLAG_PURE, 0},
    {"acos", acos,    TE_FUNCTION1 | TE_FLAG_PURE, 0},
    {"asin", asin,    TE_FUNCTION1 | TE_FLAG_PURE, 0},
    {"atan", atan,    TE_FUNCTION1 | TE_FLAG_PURE, 0},
    {"atan2", atan2,  TE_FUNCTION2 | TE_FLAG_PURE, 0},
    {"ceil", ceil,    TE_FUNCTION1 | TE_FLAG_PURE, 0},
    {"cos", cos,      TE_FUNCTION1 | TE_FLAG_PURE, 0},
    {"cosh", cosh,    TE_FUNCTION1 | TE_FLAG_PURE, 0},
    {"e", e,          TE_FUNCTION0 | TE_FLAG_PURE, 0},
    {"exp", exp,      TE_FUNCTION1 | TE_FLAG_PURE, 0},
    {"fac", fac,      TE_FUNCTION1 | TE_FLAG_PURE, 0},
    {"floor", floor,  TE_FUNCTION1 | TE_FLAG_PURE, 0},
    {"ln", log,       TE_FUNCTION1 | TE_FLAG_PURE, 0},
#ifdef TE_NAT_LOG
    {"log", log,      TE_FUNCTION1 | TE_FLAG_PURE, 0},
#else
    {"log", log10,    TE_FUNCTION1 | TE_FLAG_PURE, 0},
#endif
    {"log10", log10,  TE_FUNCTION1 | TE_FLAG_PURE, 0},
    {"ncr", ncr,      TE_FUNCTION2 | TE_FLAG_PURE, 0},
    {"npr", npr,      TE_FUNCTION2 | TE_FLAG_PURE, 0},
    {"pi", pi,        TE_FUNCTION0 | TE_FLAG_PURE, 0},
    {"pow", pow,      TE_FUNCTION2 | TE_FLAG_PURE, 0},
    {"sin", sin,      TE_FUNCTION1 | TE_FLAG_PURE, 0},
    {"sinh", sinh,    TE_FUNCTION1 | TE_FLAG_PURE, 0},
    {"sqrt", sqrt,    TE_FUNCTION1 | TE_FLAG_PURE, 0},
    {"tan", tan,      TE_FUNCTION1 | TE_FLAG_PURE, 0},
    {"tanh", tanh,    TE_FUNCTION1 | TE_FLAG_PURE, 0},
    {0, 0, 0, 0}
};

static const te_variable *find_builtin(const char *name, int len) {
    int imin = 0;
    int imax = sizeof(functions) / sizeof(te_variable) - 2;

    /*Binary search.*/
    while (imax >= imin) {
        const int i = (imin + ((imax-imin)/2));
        int c = strncmp(name, functions[i].name, len);
        if (!c) c = '\0' - functions[i].name[len];
        if (c == 0) {
            return functions + i;
        } else if (c > 0) {
            imin = i + 1;
        } else {
            imax = i - 1;
        }
    }

    return 0;
}

static const te_variable *find_lookup(const state *s, const char *name, int len) {
    int iters;
    const te_variable *var;
    if (!s->lookup) return 0;

    for (var = s->lookup, iters = s->lookup_len; iters; ++var, --iters) {
        if (strncmp(name, var->name, len) == 0 && var->name[len] == '\0') {
            return var;
        }
    }
    return 0;
}



static double add(double a, double b) {return a + b;}
static double sub(double a, double b) {return a - b;}
static double mul(double a, double b) {return a * b;}
static double divide(double a, double b) {return a / b;}
static double negate(double a) {return -a;}
static double comma(double a, double b) {(void)a; return b;}


void next_token(state *s) {
    s->type = TOK_NULL;

    do {

        if (!*s->next){
            s->type = TOK_END;
            return;
        }

        /* Try reading a number. */
        if ((s->next[0] >= '0' && s->next[0] <= '9') || s->next[0] == '.') {
            s->value = strtod(s->next, (char**)&s->next);
            s->type = TOK_NUMBER;
        } else {
            /* Look for a variable or builtin function call. */
            if (isalpha(s->next[0])) {
                const char *start;
                start = s->next;
                while (isalpha(s->next[0]) || isdigit(s->next[0]) || (s->next[0] == '_')) s->next++;
                
                const te_variable *var = find_lookup(s, start, s->next - start);
                if (!var) var = find_builtin(start, s->next - start);

                if (!var) {
                    s->type = TOK_ERROR;
                } else {
                    switch(TYPE_MASK(var->type))
                    {
                        case TE_VARIABLE:
                            s->type = TOK_VARIABLE;
                            s->bound = var->address;
                            break;

                        case TE_CLOSURE0: case TE_CLOSURE1: case TE_CLOSURE2: case TE_CLOSURE3:         /* Falls through. */
                        case TE_CLOSURE4: case TE_CLOSURE5: case TE_CLOSURE6: case TE_CLOSURE7:         /* Falls through. */
                            s->context = var->context;                                                  /* Falls through. */

                        case TE_FUNCTION0: case TE_FUNCTION1: case TE_FUNCTION2: case TE_FUNCTION3:     /* Falls through. */
                        case TE_FUNCTION4: case TE_FUNCTION5: case TE_FUNCTION6: case TE_FUNCTION7:     /* Falls through. */
                            s->type = var->type;
                            s->function = var->address;
                            break;
                    }
                }

            } else {
                /* Look for an operator or special character. */
                switch (s->next++[0]) {
                    case '+': s->type = TOK_INFIX; s->function = add; break;
                    case '-': s->type = TOK_INFIX; s->function = sub; break;
                    case '*': s->type = TOK_INFIX; s->function = mul; break;
                    case '/': s->type = TOK_INFIX; s->function = divide; break;
                    case '^': s->type = TOK_INFIX; s->function = pow; break;
                    case '%': s->type = TOK_INFIX; s->function = fmod; break;
                    case '(': s->type = TOK_OPEN; break;
                    case ')': s->type = TOK_CLOSE; break;
                    case ',': s->type = TOK_SEP; break;
                    case ' ': case '\t': case '\n': case '\r': break;
                    default: s->type = TOK_ERROR; break;
                }
            }
        }
    } while (s->type == TOK_NULL);
}


static te_expr *list(state *s);
static te_expr *expr(state *s);
static te_expr *power(state *s);

static te_expr *base(state *s) {
    /* <base>      =    <constant> | <variable> | <function-0> {"(" ")"} | <function-1> <power> | <function-X> "(" <expr> {"," <expr>} ")" | "(" <list> ")" */
    te_expr *ret;
    int arity;

    switch (TYPE_MASK(s->type)) {
        case TOK_NUMBER:
            ret = new_expr(TE_CONSTANT, 0);
            CHECK_NULL(ret);

            ret->value = s->value;
            next_token(s);
            break;

        case TOK_VARIABLE:
            ret = new_expr(TE_VARIABLE, 0);
            CHECK_NULL(ret);

            ret->bound = s->bound;
            next_token(s);
            break;

        case TE_FUNCTION0:
        case TE_CLOSURE0:
            ret = new_expr(s->type, 0);
            CHECK_NULL(ret);

            ret->function = s->function;
            if (IS_CLOSURE(s->type)) ret->parameters[0] = s->context;
            next_token(s);
            if (s->type == TOK_OPEN) {
                next_token(s);
                if (s->type != TOK_CLOSE) {
                    s->type = TOK_ERROR;
                } else {
                    next_token(s);
                }
            }
            break;

        case TE_FUNCTION1:
        case TE_CLOSURE1:
            ret = new_expr(s->type, 0);
            CHECK_NULL(ret);

            ret->function = s->function;
            if (IS_CLOSURE(s->type)) ret->parameters[1] = s->context;
            next_token(s);
            ret->parameters[0] = power(s);
            CHECK_NULL(ret->parameters[0], te_free(ret));
            break;

        case TE_FUNCTION2: case TE_FUNCTION3: case TE_FUNCTION4:
        case TE_FUNCTION5: case TE_FUNCTION6: case TE_FUNCTION7:
        case TE_CLOSURE2: case TE_CLOSURE3: case TE_CLOSURE4:
        case TE_CLOSURE5: case TE_CLOSURE6: case TE_CLOSURE7:
            arity = ARITY(s->type);

            ret = new_expr(s->type, 0);
            CHECK_NULL(ret);

            ret->function = s->function;
            if (IS_CLOSURE(s->type)) ret->parameters[arity] = s->context;
            next_token(s);

            if (s->type != TOK_OPEN) {
                s->type = TOK_ERROR;
            } else {
                int i;
                for(i = 0; i < arity; i++) {
                    next_token(s);
                    ret->parameters[i] = expr(s);
                    CHECK_NULL(ret->parameters[i], te_free(ret));

                    if(s->type != TOK_SEP) {
                        break;
                    }
                }
                if(s->type != TOK_CLOSE || i != arity - 1) {
                    s->type = TOK_ERROR;
                } else {
                    next_token(s);
                }
            }

            break;

        case TOK_OPEN:
            next_token(s);
            ret = list(s);
            CHECK_NULL(ret);

            if (s->type != TOK_CLOSE) {
                s->type = TOK_ERROR;
            } else {
                next_token(s);
            }
            break;

        default:
            ret = new_expr(0, 0);
            CHECK_NULL(ret);

            s->type = TOK_ERROR;
            ret->value = NAN;
            break;
    }

    return ret;
}


static te_expr *power(state *s) {
    /* <power>     =    {("-" | "+")} <base> */
    int sign = 1;
    while (s->type == TOK_INFIX && (s->function == add || s->function == sub)) {
        if (s->function == sub) sign = -sign;
        next_token(s);
    }

    te_expr *ret;

    if (sign == 1) {
        ret = base(s);
    } else {
        te_expr *b = base(s);
        CHECK_NULL(b);

        ret = NEW_EXPR(TE_FUNCTION1 | TE_FLAG_PURE, b);
        CHECK_NULL(ret, te_free(b));

        ret->function = negate;
    }

    return ret;
}

#ifdef TE_POW_FROM_RIGHT
static te_expr *factor(state *s) {
    /* <factor>    =    <power> {"^" <power>} */
    te_expr *ret = power(s);
    CHECK_NULL(ret);

    int neg = 0;

    if (ret->type == (TE_FUNCTION1 | TE_FLAG_PURE) && ret->function == negate) {
        te_expr *se = ret->parameters[0];
        free(ret);
        ret = se;
        neg = 1;
    }

    te_expr *insertion = 0;

    while (s->type == TOK_INFIX && (s->function == pow)) {
        te_fun2 t = s->function;
        next_token(s);

        if (insertion) {
            /* Make exponentiation go right-to-left. */
            te_expr *p = power(s);
            CHECK_NULL(p, te_free(ret));

            te_expr *insert = NEW_EXPR(TE_FUNCTION2 | TE_FLAG_PURE, insertion->parameters[1], p);
            CHECK_NULL(insert, te_free(p), te_free(ret));

            insert->function = t;
            insertion->parameters[1] = insert;
            insertion = insert;
        } else {
            te_expr *p = power(s);
            CHECK_NULL(p, te_free(ret));

            te_expr *prev = ret;
            ret = NEW_EXPR(TE_FUNCTION2 | TE_FLAG_PURE, ret, p);
            CHECK_NULL(ret, te_free(p), te_free(prev));

            ret->function = t;
            insertion = ret;
        }
    }

    if (neg) {
        te_expr *prev = ret;
        ret = NEW_EXPR(TE_FUNCTION1 | TE_FLAG_PURE, ret);
        CHECK_NULL(ret, te_free(prev));

        ret->function = negate;
    }

    return ret;
}
#else
static te_expr *factor(state *s) {
    /* <factor>    =    <power> {"^" <power>} */
    te_expr *ret = power(s);
    CHECK_NULL(ret);

    while (s->type == TOK_INFIX && (s->function == pow)) {
        te_fun2 t = s->function;
        next_token(s);
        te_expr *p = power(s);
        CHECK_NULL(p, te_free(ret));

        te_expr *prev = ret;
        ret = NEW_EXPR(TE_FUNCTION2 | TE_FLAG_PURE, ret, p);
        CHECK_NULL(ret, te_free(p), te_free(prev));

        ret->function = t;
    }

    return ret;
}
#endif



static te_expr *term(state *s) {
    /* <term>      =    <factor> {("*" | "/" | "%") <factor>} */
    te_expr *ret = factor(s);
    CHECK_NULL(ret);

    while (s->type == TOK_INFIX && (s->function == mul || s->function == divide || s->function == fmod)) {
        te_fun2 t = s->function;
        next_token(s);
        te_expr *f = factor(s);
        CHECK_NULL(f, te_free(ret));

        te_expr *prev = ret;
        ret = NEW_EXPR(TE_FUNCTION2 | TE_FLAG_PURE, ret, f);
        CHECK_NULL(ret, te_free(f), te_free(prev));

        ret->function = t;
    }

    return ret;
}


static te_expr *expr(state *s) {
    /* <expr>      =    <term> {("+" | "-") <term>} */
    te_expr *ret = term(s);
    CHECK_NULL(ret);

    while (s->type == TOK_INFIX && (s->function == add || s->function == sub)) {
        te_fun2 t = s->function;
        next_token(s);
        te_expr *te = term(s);
        CHECK_NULL(te, te_free(ret));

        te_expr *prev = ret;
        ret = NEW_EXPR(TE_FUNCTION2 | TE_FLAG_PURE, ret, te);
        CHECK_NULL(ret, te_free(te), te_free(prev));

        ret->function = t;
    }

    return ret;
}


static te_expr *list(state *s) {
    /* <list>      =    <expr> {"," <expr>} */
    te_expr *ret = expr(s);
    CHECK_NULL(ret);

    while (s->type == TOK_SEP) {
        next_token(s);
        te_expr *e = expr(s);
        CHECK_NULL(e, te_free(ret));

        te_expr *prev = ret;
        ret = NEW_EXPR(TE_FUNCTION2 | TE_FLAG_PURE, ret, e);
        CHECK_NULL(ret, te_free(e), te_free(prev));

        ret->function = comma;
    }

    return ret;
}


#define TE_FUN(...) ((double(*)(__VA_ARGS__))n->function)
#define M(e) te_eval(n->parameters[e])


double te_eval(const te_expr *n) {
    if (!n) return NAN;

    switch(TYPE_MASK(n->type)) {
        case TE_CONSTANT: return n->value;
        case TE_VARIABLE: return *n->bound;

        case TE_FUNCTION0: case TE_FUNCTION1: case TE_FUNCTION2: case TE_FUNCTION3:
        case TE_FUNCTION4: case TE_FUNCTION5: case TE_FUNCTION6: case TE_FUNCTION7:
            switch(ARITY(n->type)) {
                case 0: return TE_FUN(void)();
                case 1: return TE_FUN(double)(M(0));
                case 2: return TE_FUN(double, double)(M(0), M(1));
                case 3: return TE_FUN(double, double, double)(M(0), M(1), M(2));
                case 4: return TE_FUN(double, double, double, double)(M(0), M(1), M(2), M(3));
                case 5: return TE_FUN(double, double, double, double, double)(M(0), M(1), M(2), M(3), M(4));
                case 6: return TE_FUN(double, double, double, double, double, double)(M(0), M(1), M(2), M(3), M(4), M(5));
                case 7: return TE_FUN(double, double, double, double, double, double, double)(M(0), M(1), M(2), M(3), M(4), M(5), M(6));
                default: return NAN;
            }

        case TE_CLOSURE0: case TE_CLOSURE1: case TE_CLOSURE2: case TE_CLOSURE3:
        case TE_CLOSURE4: case TE_CLOSURE5: case TE_CLOSURE6: case TE_CLOSURE7:
            switch(ARITY(n->type)) {
                case 0: return TE_FUN(void*)(n->parameters[0]);
                case 1: return TE_FUN(void*, double)(n->parameters[1], M(0));
                case 2: return TE_FUN(void*, double, double)(n->parameters[2], M(0), M(1));
                case 3: return TE_FUN(void*, double, double, double)(n->parameters[3], M(0), M(1), M(2));
                case 4: return TE_FUN(void*, double, double, double, double)(n->parameters[4], M(0), M(1), M(2), M(3));
                case 5: return TE_FUN(void*, double, double, double, double, double)(n->parameters[5], M(0), M(1), M(2), M(3), M(4));
                case 6: return TE_FUN(void*, double, double, double, double, double, double)(n->parameters[6], M(0), M(1), M(2), M(3), M(4), M(5));
                case 7: return TE_FUN(void*, double, double, double, double, double, double, double)(n->parameters[7], M(0), M(1), M(2), M(3), M(4), M(5), M(6));
                default: return NAN;
            }

        default: return NAN;
    }

}

#undef TE_FUN
#undef M

static void optimize(te_expr *n) {
    /* Evaluates as much as possible. */
    if (n->type == TE_CONSTANT) return;
    if (n->type == TE_VARIABLE) return;

    /* Only optimize out functions flagged as pure. */
    if (IS_PURE(n->type)) {
        const int arity = ARITY(n->type);
        int known = 1;
        int i;
        for (i = 0; i < arity; ++i) {
            optimize(n->parameters[i]);
            if (((te_expr*)(n->parameters[i]))->type != TE_CONSTANT) {
                known = 0;
            }
        }
        if (known) {
            const double value = te_eval(n);
            te_free_parameters(n);
            n->type = TE_CONSTANT;
            n->value = value;
        }
    }
}


te_expr *te_compile(const char *expression, const te_variable *variables, int var_count, int *error) {
    state s;
    s.start = s.next = expression;
    s.lookup = variables;
    s.lookup_len = var_count;

    next_token(&s);
    te_expr *root = list(&s);
    if (root == NULL) {
        if (error) *error = -1;
        return NULL;
    }

    if (s.type != TOK_END) {
        te_free(root);
        if (error) {
            *error = (s.next - s.start);
            if (*error == 0) *error = 1;
        }
        return 0;
    } else {
        optimize(root);
        if (error) *error = 0;
        return root;
    }
}




typedef enum te_program_opcode {
    TE_OP_PUSH_CONST = 1,
    TE_OP_PUSH_VAR,
    TE_OP_NEG,
    TE_OP_ADD,
    TE_OP_SUB,
    TE_OP_MUL,
    TE_OP_DIV,
    TE_OP_POW,
    TE_OP_COMMA,
    TE_OP_ABS,
    TE_OP_ACOS,
    TE_OP_ASIN,
    TE_OP_ATAN,
    TE_OP_ATAN2,
    TE_OP_CEIL,
    TE_OP_COS,
    TE_OP_COSH,
    TE_OP_EXP,
    TE_OP_FAC,
    TE_OP_FLOOR,
    TE_OP_LOG,
    TE_OP_LOG10,
    TE_OP_NCR,
    TE_OP_NPR,
    TE_OP_SIN,
    TE_OP_SINH,
    TE_OP_SQRT,
    TE_OP_TAN,
    TE_OP_TANH,
    TE_OP_CALL0,
    TE_OP_CALL1,
    TE_OP_CALL2,
    TE_OP_CALL3,
    TE_OP_CALL4,
    TE_OP_CALL5,
    TE_OP_CALL6,
    TE_OP_CALL7,
    TE_OP_CLOSURE0,
    TE_OP_CLOSURE1,
    TE_OP_CLOSURE2,
    TE_OP_CLOSURE3,
    TE_OP_CLOSURE4,
    TE_OP_CLOSURE5,
    TE_OP_CLOSURE6,
    TE_OP_CLOSURE7
} te_program_opcode;

typedef struct te_program_instr {
    unsigned char opcode;
    unsigned char arity;
    unsigned short reserved;
    union {
        double value;
        int var_index;
        const void *function;
    } data;
    void *context;
} te_program_instr;

struct te_program {
    int count;
    int capacity;
    te_program_instr *instructions;
    double *stack;
};

static int te_program_reserve(te_program *program, int extra) {
    if (program->count + extra <= program->capacity) return 1;
    int new_capacity = program->capacity ? program->capacity * 2 : 32;
    while (new_capacity < program->count + extra) {
        new_capacity *= 2;
    }
    te_program_instr *instructions = (te_program_instr*)realloc(program->instructions, (size_t)new_capacity * sizeof(te_program_instr));
    if (!instructions) return 0;
    program->instructions = instructions;
    program->capacity = new_capacity;
    return 1;
}

static int te_program_emit(te_program *program, te_program_instr instr) {
    if (!te_program_reserve(program, 1)) return 0;
    program->instructions[program->count++] = instr;
    return 1;
}

static int te_find_var_index(const te_variable *variables, int var_count, const double *bound) {
    int i;
    for (i = 0; i < var_count; ++i) {
        if ((const double*)variables[i].address == bound) return i;
    }
    return -1;
}

static te_program_opcode te_classify_function(const te_expr *n) {
    const int type = TYPE_MASK(n->type);
    if (type == TE_FUNCTION1) {
        if (n->function == (const void*)negate) return TE_OP_NEG;
        if (n->function == (const void*)fabs) return TE_OP_ABS;
        if (n->function == (const void*)acos) return TE_OP_ACOS;
        if (n->function == (const void*)asin) return TE_OP_ASIN;
        if (n->function == (const void*)atan) return TE_OP_ATAN;
        if (n->function == (const void*)ceil) return TE_OP_CEIL;
        if (n->function == (const void*)cos) return TE_OP_COS;
        if (n->function == (const void*)cosh) return TE_OP_COSH;
        if (n->function == (const void*)exp) return TE_OP_EXP;
        if (n->function == (const void*)fac) return TE_OP_FAC;
        if (n->function == (const void*)floor) return TE_OP_FLOOR;
        if (n->function == (const void*)log) return TE_OP_LOG;
        if (n->function == (const void*)log10) return TE_OP_LOG10;
        if (n->function == (const void*)sin) return TE_OP_SIN;
        if (n->function == (const void*)sinh) return TE_OP_SINH;
        if (n->function == (const void*)sqrt) return TE_OP_SQRT;
        if (n->function == (const void*)tan) return TE_OP_TAN;
        if (n->function == (const void*)tanh) return TE_OP_TANH;
        return TE_OP_CALL1;
    }
    if (type == TE_FUNCTION2) {
        if (n->function == (const void*)add) return TE_OP_ADD;
        if (n->function == (const void*)sub) return TE_OP_SUB;
        if (n->function == (const void*)mul) return TE_OP_MUL;
        if (n->function == (const void*)divide) return TE_OP_DIV;
        if (n->function == (const void*)pow) return TE_OP_POW;
        if (n->function == (const void*)atan2) return TE_OP_ATAN2;
        if (n->function == (const void*)comma) return TE_OP_COMMA;
        if (n->function == (const void*)ncr) return TE_OP_NCR;
        if (n->function == (const void*)npr) return TE_OP_NPR;
        return TE_OP_CALL2;
    }
    switch (type) {
        case TE_FUNCTION0: return TE_OP_CALL0;
        case TE_FUNCTION3: return TE_OP_CALL3;
        case TE_FUNCTION4: return TE_OP_CALL4;
        case TE_FUNCTION5: return TE_OP_CALL5;
        case TE_FUNCTION6: return TE_OP_CALL6;
        case TE_FUNCTION7: return TE_OP_CALL7;
        case TE_CLOSURE0: return TE_OP_CLOSURE0;
        case TE_CLOSURE1: return TE_OP_CLOSURE1;
        case TE_CLOSURE2: return TE_OP_CLOSURE2;
        case TE_CLOSURE3: return TE_OP_CLOSURE3;
        case TE_CLOSURE4: return TE_OP_CLOSURE4;
        case TE_CLOSURE5: return TE_OP_CLOSURE5;
        case TE_CLOSURE6: return TE_OP_CLOSURE6;
        case TE_CLOSURE7: return TE_OP_CLOSURE7;
        default: return 0;
    }
}

static int te_compile_program_node(te_program *program, const te_expr *n, const te_variable *variables, int var_count) {
    const int type = TYPE_MASK(n->type);
    int i;
    te_program_instr instr;
    memset(&instr, 0, sizeof(instr));

    if (type == TE_CONSTANT) {
        instr.opcode = TE_OP_PUSH_CONST;
        instr.data.value = n->value;
        return te_program_emit(program, instr);
    }

    if (type == TE_VARIABLE) {
        const int var_index = te_find_var_index(variables, var_count, n->bound);
        if (var_index < 0) return 0;
        instr.opcode = TE_OP_PUSH_VAR;
        instr.data.var_index = var_index;
        return te_program_emit(program, instr);
    }

    for (i = 0; i < ARITY(n->type); ++i) {
        if (!te_compile_program_node(program, n->parameters[i], variables, var_count)) {
            return 0;
        }
    }

    instr.opcode = (unsigned char)te_classify_function(n);
    if (!instr.opcode) return 0;
    instr.arity = (unsigned char)ARITY(n->type);
    instr.data.function = n->function;
    if (TYPE_MASK(n->type) >= TE_CLOSURE0 && TYPE_MASK(n->type) <= TE_CLOSURE7) {
        instr.context = n->parameters[instr.arity];
    }
    return te_program_emit(program, instr);
}

te_program *te_compile_program(const te_expr *n, const te_variable *variables, int var_count) {
    te_program *program;
    if (!n) return NULL;
    program = (te_program*)calloc(1, sizeof(te_program));
    if (!program) return NULL;
    if (!te_compile_program_node(program, n, variables, var_count)) {
        te_free_program(program);
        return NULL;
    }
    program->stack = (double*)malloc((size_t)(program->count > 0 ? program->count : 1) * sizeof(double));
    if (!program->stack) {
        te_free_program(program);
        return NULL;
    }
    return program;
}

void te_free_program(te_program *program) {
    if (!program) return;
    free(program->instructions);
    free(program->stack);
    free(program);
}

#define TE_CALL0(FN) ((double(*)(void))(FN))()
#define TE_CALL1(FN, A0) ((double(*)(double))(FN))((A0))
#define TE_CALL2(FN, A0, A1) ((double(*)(double, double))(FN))((A0), (A1))
#define TE_CALL3(FN, A0, A1, A2) ((double(*)(double, double, double))(FN))((A0), (A1), (A2))
#define TE_CALL4(FN, A0, A1, A2, A3) ((double(*)(double, double, double, double))(FN))((A0), (A1), (A2), (A3))
#define TE_CALL5(FN, A0, A1, A2, A3, A4) ((double(*)(double, double, double, double, double))(FN))((A0), (A1), (A2), (A3), (A4))
#define TE_CALL6(FN, A0, A1, A2, A3, A4, A5) ((double(*)(double, double, double, double, double, double))(FN))((A0), (A1), (A2), (A3), (A4), (A5))
#define TE_CALL7(FN, A0, A1, A2, A3, A4, A5, A6) ((double(*)(double, double, double, double, double, double, double))(FN))((A0), (A1), (A2), (A3), (A4), (A5), (A6))
#define TE_CCALL0(FN, CTX) ((double(*)(void*))(FN))((CTX))
#define TE_CCALL1(FN, CTX, A0) ((double(*)(void*, double))(FN))((CTX), (A0))
#define TE_CCALL2(FN, CTX, A0, A1) ((double(*)(void*, double, double))(FN))((CTX), (A0), (A1))
#define TE_CCALL3(FN, CTX, A0, A1, A2) ((double(*)(void*, double, double, double))(FN))((CTX), (A0), (A1), (A2))
#define TE_CCALL4(FN, CTX, A0, A1, A2, A3) ((double(*)(void*, double, double, double, double))(FN))((CTX), (A0), (A1), (A2), (A3))
#define TE_CCALL5(FN, CTX, A0, A1, A2, A3, A4) ((double(*)(void*, double, double, double, double, double))(FN))((CTX), (A0), (A1), (A2), (A3), (A4))
#define TE_CCALL6(FN, CTX, A0, A1, A2, A3, A4, A5) ((double(*)(void*, double, double, double, double, double, double))(FN))((CTX), (A0), (A1), (A2), (A3), (A4), (A5))
#define TE_CCALL7(FN, CTX, A0, A1, A2, A3, A4, A5, A6) ((double(*)(void*, double, double, double, double, double, double, double))(FN))((CTX), (A0), (A1), (A2), (A3), (A4), (A5), (A6))

double te_eval_program(const te_program *program, const double *variables) {
    int sp = 0;
    int i;
    double *stack;
    if (!program || !program->stack) return NAN;
    stack = program->stack;

    for (i = 0; i < program->count; ++i) {
        const te_program_instr *instr = &program->instructions[i];
        switch (instr->opcode) {
            case TE_OP_PUSH_CONST:
                stack[sp++] = instr->data.value;
                break;
            case TE_OP_PUSH_VAR:
                stack[sp++] = variables[instr->data.var_index];
                break;
            case TE_OP_NEG:
                stack[sp - 1] = -stack[sp - 1];
                break;
            case TE_OP_ADD:
                --sp; stack[sp - 1] = stack[sp - 1] + stack[sp];
                break;
            case TE_OP_SUB:
                --sp; stack[sp - 1] = stack[sp - 1] - stack[sp];
                break;
            case TE_OP_MUL:
                --sp; stack[sp - 1] = stack[sp - 1] * stack[sp];
                break;
            case TE_OP_DIV:
                --sp; stack[sp - 1] = stack[sp - 1] / stack[sp];
                break;
            case TE_OP_POW:
                --sp; stack[sp - 1] = pow(stack[sp - 1], stack[sp]);
                break;
            case TE_OP_COMMA:
                --sp; stack[sp - 1] = stack[sp];
                break;
            case TE_OP_ABS:
                stack[sp - 1] = fabs(stack[sp - 1]);
                break;
            case TE_OP_ACOS:
                stack[sp - 1] = acos(stack[sp - 1]);
                break;
            case TE_OP_ASIN:
                stack[sp - 1] = asin(stack[sp - 1]);
                break;
            case TE_OP_ATAN:
                stack[sp - 1] = atan(stack[sp - 1]);
                break;
            case TE_OP_ATAN2:
                --sp; stack[sp - 1] = atan2(stack[sp - 1], stack[sp]);
                break;
            case TE_OP_CEIL:
                stack[sp - 1] = ceil(stack[sp - 1]);
                break;
            case TE_OP_COS:
                stack[sp - 1] = cos(stack[sp - 1]);
                break;
            case TE_OP_COSH:
                stack[sp - 1] = cosh(stack[sp - 1]);
                break;
            case TE_OP_EXP:
                stack[sp - 1] = exp(stack[sp - 1]);
                break;
            case TE_OP_FAC:
                stack[sp - 1] = fac(stack[sp - 1]);
                break;
            case TE_OP_FLOOR:
                stack[sp - 1] = floor(stack[sp - 1]);
                break;
            case TE_OP_LOG:
                stack[sp - 1] = log(stack[sp - 1]);
                break;
            case TE_OP_LOG10:
                stack[sp - 1] = log10(stack[sp - 1]);
                break;
            case TE_OP_NCR:
                --sp; stack[sp - 1] = ncr(stack[sp - 1], stack[sp]);
                break;
            case TE_OP_NPR:
                --sp; stack[sp - 1] = npr(stack[sp - 1], stack[sp]);
                break;
            case TE_OP_SIN:
                stack[sp - 1] = sin(stack[sp - 1]);
                break;
            case TE_OP_SINH:
                stack[sp - 1] = sinh(stack[sp - 1]);
                break;
            case TE_OP_SQRT:
                stack[sp - 1] = sqrt(stack[sp - 1]);
                break;
            case TE_OP_TAN:
                stack[sp - 1] = tan(stack[sp - 1]);
                break;
            case TE_OP_TANH:
                stack[sp - 1] = tanh(stack[sp - 1]);
                break;
            case TE_OP_CALL0:
                stack[sp++] = TE_CALL0(instr->data.function);
                break;
            case TE_OP_CALL1:
                stack[sp - 1] = TE_CALL1(instr->data.function, stack[sp - 1]);
                break;
            case TE_OP_CALL2:
                --sp; stack[sp - 1] = TE_CALL2(instr->data.function, stack[sp - 1], stack[sp]);
                break;
            case TE_OP_CALL3:
                sp -= 2; stack[sp - 1] = TE_CALL3(instr->data.function, stack[sp - 1], stack[sp], stack[sp + 1]);
                break;
            case TE_OP_CALL4:
                sp -= 3; stack[sp - 1] = TE_CALL4(instr->data.function, stack[sp - 1], stack[sp], stack[sp + 1], stack[sp + 2]);
                break;
            case TE_OP_CALL5:
                sp -= 4; stack[sp - 1] = TE_CALL5(instr->data.function, stack[sp - 1], stack[sp], stack[sp + 1], stack[sp + 2], stack[sp + 3]);
                break;
            case TE_OP_CALL6:
                sp -= 5; stack[sp - 1] = TE_CALL6(instr->data.function, stack[sp - 1], stack[sp], stack[sp + 1], stack[sp + 2], stack[sp + 3], stack[sp + 4]);
                break;
            case TE_OP_CALL7:
                sp -= 6; stack[sp - 1] = TE_CALL7(instr->data.function, stack[sp - 1], stack[sp], stack[sp + 1], stack[sp + 2], stack[sp + 3], stack[sp + 4], stack[sp + 5]);
                break;
            case TE_OP_CLOSURE0:
                stack[sp++] = TE_CCALL0(instr->data.function, instr->context);
                break;
            case TE_OP_CLOSURE1:
                stack[sp - 1] = TE_CCALL1(instr->data.function, instr->context, stack[sp - 1]);
                break;
            case TE_OP_CLOSURE2:
                --sp; stack[sp - 1] = TE_CCALL2(instr->data.function, instr->context, stack[sp - 1], stack[sp]);
                break;
            case TE_OP_CLOSURE3:
                sp -= 2; stack[sp - 1] = TE_CCALL3(instr->data.function, instr->context, stack[sp - 1], stack[sp], stack[sp + 1]);
                break;
            case TE_OP_CLOSURE4:
                sp -= 3; stack[sp - 1] = TE_CCALL4(instr->data.function, instr->context, stack[sp - 1], stack[sp], stack[sp + 1], stack[sp + 2]);
                break;
            case TE_OP_CLOSURE5:
                sp -= 4; stack[sp - 1] = TE_CCALL5(instr->data.function, instr->context, stack[sp - 1], stack[sp], stack[sp + 1], stack[sp + 2], stack[sp + 3]);
                break;
            case TE_OP_CLOSURE6:
                sp -= 5; stack[sp - 1] = TE_CCALL6(instr->data.function, instr->context, stack[sp - 1], stack[sp], stack[sp + 1], stack[sp + 2], stack[sp + 3], stack[sp + 4]);
                break;
            case TE_OP_CLOSURE7:
                sp -= 6; stack[sp - 1] = TE_CCALL7(instr->data.function, instr->context, stack[sp - 1], stack[sp], stack[sp + 1], stack[sp + 2], stack[sp + 3], stack[sp + 4], stack[sp + 5]);
                break;
            default:
                return NAN;
        }
    }

    return sp == 1 ? stack[0] : NAN;
}

#undef TE_CALL0
#undef TE_CALL1
#undef TE_CALL2
#undef TE_CALL3
#undef TE_CALL4
#undef TE_CALL5
#undef TE_CALL6
#undef TE_CALL7
#undef TE_CCALL0
#undef TE_CCALL1
#undef TE_CCALL2
#undef TE_CCALL3
#undef TE_CCALL4
#undef TE_CCALL5
#undef TE_CCALL6
#undef TE_CCALL7
double te_interp(const char *expression, int *error) {
    te_expr *n = te_compile(expression, 0, 0, error);

    double ret;
    if (n) {
        ret = te_eval(n);
        te_free(n);
    } else {
        ret = NAN;
    }
    return ret;
}

static void pn (const te_expr *n, int depth) {
    int i, arity;
    printf("%*s", depth, "");

    switch(TYPE_MASK(n->type)) {
    case TE_CONSTANT: printf("%f\n", n->value); break;
    case TE_VARIABLE: printf("bound %p\n", n->bound); break;

    case TE_FUNCTION0: case TE_FUNCTION1: case TE_FUNCTION2: case TE_FUNCTION3:
    case TE_FUNCTION4: case TE_FUNCTION5: case TE_FUNCTION6: case TE_FUNCTION7:
    case TE_CLOSURE0: case TE_CLOSURE1: case TE_CLOSURE2: case TE_CLOSURE3:
    case TE_CLOSURE4: case TE_CLOSURE5: case TE_CLOSURE6: case TE_CLOSURE7:
         arity = ARITY(n->type);
         printf("f%d", arity);
         for(i = 0; i < arity; i++) {
             printf(" %p", n->parameters[i]);
         }
         printf("\n");
         for(i = 0; i < arity; i++) {
             pn(n->parameters[i], depth + 1);
         }
         break;
    }
}


void te_print(const te_expr *n) {
    pn(n, 0);
}

