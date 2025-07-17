from django import template

register = template.Library()


@register.simple_tag
def col_class_list(breakpoints, n_cols):
    if breakpoints:
        class_list = []

        for screen_size, max_cols in breakpoints.items():
            col_size = int(12 / min(max_cols, n_cols))
            if screen_size == "sm":
                class_name = f"col-{col_size}"
            else:
                class_name = f"col-{screen_size}-{col_size}"

            class_list.append(class_name)

        return " ".join(class_list)

    return "col-md"


@register.simple_tag
def display_class_list(breakpoints, col_index):
    if breakpoints and col_index > 1:
        class_list = ["d-none"]

        for screen_size, max_cols in breakpoints.items():
            if col_index <= max_cols:
                if screen_size == "sm":
                    class_list = ["d-block"]
                else:
                    class_list.append(f" d-{screen_size}-block")
                break

        return " ".join(class_list)

    return ""
