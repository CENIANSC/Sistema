import streamlit as st
import compras

st.set_page_config(
    page_title="Sistema de Compras",
    layout="wide"
)

st.title("Sistema de Compras")

st.header("Nueva Orden de Compra")

categorias = compras.categorias_con_productos()

items = []

for categoria, productos in categorias.items():

    with st.expander(categoria, expanded=True):

        col1, col2 = st.columns(2)

        mitad = len(productos) // 2 + 1

        productos_izquierda = productos[:mitad]
        productos_derecha = productos[mitad:]

        with col1:

            for producto in productos_izquierda:

                cantidad = st.number_input(
                    producto,
                    min_value=0,
                    step=1,
                    value=0,
                    key=f"izq_{producto}"
                )

                if cantidad > 0:

                    items.append({
                        "Producto": producto,
                        "Cantidad": cantidad
                    })

        with col2:

            for producto in productos_derecha:

                cantidad = st.number_input(
                    producto,
                    min_value=0,
                    step=1,
                    value=0,
                    key=f"der_{producto}"
                )

                if cantidad > 0:

                    items.append({
                        "Producto": producto,
                        "Cantidad": cantidad
                    })

st.divider()

st.subheader("Resumen")

st.write(
    f"Productos seleccionados: {len(items)}"
)

if len(items) > 0:

    st.dataframe(items)

if st.button("GENERAR ORDEN DE COMPRA"):

    if len(items) == 0:

        st.warning(
            "Debe capturar al menos un producto."
        )

    else:

        try:

            resultado = compras.generar_oc_desde_items(
                items
            )

            st.success(
                f"Orden generada correctamente: {resultado['folio']}"
            )

            st.write(
                f"PDF generado: {resultado['pdf']}"
            )

            st.dataframe(
                resultado["pedido"]
            )

        except Exception as e:

            st.error(
                f"Error al generar la orden: {e}"
            )
