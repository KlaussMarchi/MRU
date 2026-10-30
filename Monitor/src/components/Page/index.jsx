import './styles.css'


// A TELA INTEIRA SEM ROLAR: CABEÇALHO NUMA LINHA E O CORPO NO RESTO, ONDE SÓ O CONTEÚDO DE CADA PAINEL ROLA SE PRECISAR
export default function Page({title, subtitle, actions, className = '', children}){
    return (
        <main className={`Page ${className}`}>
            <header className='PageHeader'>
                <div className='PageHeading'>
                    <h1 className='PageTitle'>{title}</h1>
                    {subtitle && <div className='PageSubtitle' title={typeof subtitle == 'string' ? subtitle : undefined}>{subtitle}</div>}
                </div>

                {actions && <div className='PageActions'>{actions}</div>}
            </header>

            <div className='PageBody'>{children}</div>
        </main>
    )
}
